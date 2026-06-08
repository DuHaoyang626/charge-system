"""
计费服务 — BillingService

职责：
- 充电完成后计算阶梯电价 + 服务费
- 生成账单概览和分时段详单
- 按日期查询历史账单

计费规则：
    总费用 = 电费 + 服务费
    电费 = Σ(各时段充电量 × 对应时段电价)
    服务费 = 基础服务费(baseFee) + 时长系数(timeCoefficient × 充电时长)
"""

from datetime import datetime, timedelta

from src.db.database import get_session
from src.db.models import BillingRecord, ChargingPile, ChargingSession, DetailedBill, PileTariffConfig
from src.config import config
from src.enums import LogModule
from src.utils.logger import logger


class BillingService:
    """充电计费服务"""

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _get_period(dt: datetime, periods) -> str:
        """判断给定时间所属的计费时段

        Args:
            dt: 时间点
            periods: TimePeriods 对象，含 peak/valley/normal 各时段列表

        Returns:
            "peak" | "normal" | "valley"
        """
        time_str = dt.strftime("%H:%M")
        for name in ("peak", "valley"):
            for r in getattr(periods, name, []):
                if r.start <= time_str < r.end:
                    return name
        return "normal"

    @staticmethod
    def _generate_bill_id(session) -> str:
        """生成账单编号  B{YYYYMMDD}{XXX}  (当日递增)"""
        today = datetime.now().strftime("%Y%m%d")
        count = session.query(BillingRecord).filter(
            BillingRecord.bill_id.like(f"B{today}%")
        ).count()
        return f"B{today}{count + 1:03d}"

    @staticmethod
    def _get_prices(pile_id: str):
        """获取充电桩的计费规则

        优先读取 pile_tariff_configs 表的桩级独立配置，
        若未找到则使用 config/application.yml 中的全局默认值。

        Returns:
            dict with keys: peak_price, normal_price, valley_price, base_fee, time_coefficient
        """
        db = get_session()
        try:
            tariff = (
                db.query(PileTariffConfig)
                .filter(PileTariffConfig.pile_id == pile_id)
                .first()
            )
            if tariff:
                return {
                    "peak_price": float(tariff.peak_price),
                    "normal_price": float(tariff.normal_price),
                    "valley_price": float(tariff.valley_price),
                    "base_fee": float(tariff.base_service_fee),
                    "time_coefficient": float(tariff.time_coefficient),
                }
        finally:
            db.close()

        # 使用全局默认配置
        dp = config.billing.default_prices
        sf = config.billing.service_fee
        return {
            "peak_price": dp.peak_price,
            "normal_price": dp.normal_price,
            "valley_price": dp.valley_price,
            "base_fee": sf.base_fee,
            "time_coefficient": sf.time_coefficient,
        }

    # ------------------------------------------------------------------
    # calculateBill: 充电完成后计算费用
    # ------------------------------------------------------------------
    def calculate_bill(self, session_id: str) -> dict:
        """计算充电账单

        根据充电会话的起止时间和各时段电价计算费用，
        并按时段拆分详单。

        Args:
            session_id: 充电会话编号

        Returns:
            {"success": True, "bill_id": "...", "total_charge_fee": ...,
             "total_service_fee": ..., "total_fee": ..., "periods": [...]}

        Raises:
            ValueError: 充电会话不存在
        """
        db = get_session()
        try:
            # ── 1. 检查是否已为该会话生成过账单（幂等性） ──────
            existing = (
                db.query(BillingRecord)
                .filter(BillingRecord.session_id == session_id)
                .first()
            )
            if existing:
                return self.get_detailed_bill(existing.bill_id)

            # ── 2. 查询充电会话 ────────────────────────────
            cs = (
                db.query(ChargingSession)
                .filter(ChargingSession.session_id == session_id)
                .first()
            )
            if not cs:
                raise ValueError(f"充电会话不存在: {session_id}")

            # ── 3. 获取计费参数 ────────────────────────────
            prices = self._get_prices(cs.pile_id)
            time_periods = config.billing.time_periods
            sf_conf = config.billing.service_fee

            start = cs.start_time
            end = cs.end_time if cs.end_time else datetime.now()
            charged_kwh = float(cs.charged_power_kwh)

            duration_minutes = max((end - start).total_seconds() / 60.0, 0)

            # ── 4. 生成账单编号 ────────────────────────────
            bill_id = self._generate_bill_id(db)
            bill_date = start.date()

            # ── 5. 无充电量或零时长 → 仅基础服务费 ──────────
            if duration_minutes == 0 or charged_kwh <= 0:
                total_charge_fee = 0.0
                total_service_fee = sf_conf.base_fee
                total_fee = total_charge_fee + total_service_fee

                record = BillingRecord(
                    bill_id=bill_id,
                    session_id=session_id,
                    car_id=cs.car_id,
                    date=bill_date,
                    pile_id=cs.pile_id,
                    charge_amount=0.0,
                    charge_duration=0.0,
                    start_time=start,
                    end_time=end,
                    total_charge_fee=0.0,
                    total_service_fee=total_service_fee,
                    total_fee=total_fee,
                    payment_status="UNPAID",
                )
                db.add(record)
                db.commit()

                logger.info(
                    LogModule.BILLING,
                    f"[计费] 账单生成(空) (bill_id: {bill_id}, session: {session_id})",
                )

                return {
                    "success": True,
                    "bill_id": bill_id,
                    "session_id": session_id,
                    "car_id": cs.car_id,
                    "pile_id": cs.pile_id,
                    "date": bill_date.isoformat(),
                    "charge_amount_kwh": 0.0,
                    "charge_duration_minutes": 0.0,
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                    "total_charge_fee": 0.0,
                    "total_service_fee": total_service_fee,
                    "total_fee": total_fee,
                    "payment_status": "UNPAID",
                    "periods": [],
                }

            # ── 6. 分钟级遍历，累计各时段充电量 ────────────
            rate_per_min = charged_kwh / duration_minutes  # kWh/分钟

            # period_name -> {kwh, minutes, start, end}
            period_data: dict = {}

            current = start
            while current < end:
                minute_end = min(current + timedelta(minutes=1), end)
                span_minutes = (minute_end - current).total_seconds() / 60.0

                period = self._get_period(current, time_periods)

                if period not in period_data:
                    period_data[period] = {
                        "kwh": 0.0,
                        "minutes": 0.0,
                        "start": current,
                        "end": minute_end,
                    }
                else:
                    period_data[period]["end"] = minute_end

                period_data[period]["kwh"] += rate_per_min * span_minutes
                period_data[period]["minutes"] += span_minutes

                current = minute_end

            # ── 7. 计算电费和服务费 ────────────────────────
            price_map = {
                "peak": prices["peak_price"],
                "normal": prices["normal_price"],
                "valley": prices["valley_price"],
            }

            # 总服务费
            total_service_fee_value = sf_conf.base_fee + sf_conf.time_coefficient * duration_minutes

            total_charge_fee = 0.0
            periods_result = []

            for period_name in ("peak", "normal", "valley"):
                pd = period_data.get(period_name)
                if pd is None:
                    continue

                kwh = pd["kwh"]
                unit_price = price_map[period_name]
                charge_fee = kwh * unit_price

                # 服务费按充电量比例分摊到各时段
                period_service_fee = total_service_fee_value * (kwh / charged_kwh)

                subtotal = charge_fee + period_service_fee
                total_charge_fee += charge_fee

                periods_result.append({
                    "period_name": period_name,
                    "period_start": pd["start"],
                    "period_end": pd["end"],
                    "charge_kwh": kwh,
                    "unit_price": unit_price,
                    "charge_fee": charge_fee,
                    "service_fee": period_service_fee,
                    "subtotal_fee": subtotal,
                })

            total_fee = total_charge_fee + total_service_fee_value

            # ── 8. 写入数据库 ────────────────────────────
            record = BillingRecord(
                bill_id=bill_id,
                session_id=session_id,
                car_id=cs.car_id,
                date=bill_date,
                pile_id=cs.pile_id,
                charge_amount=round(charged_kwh, 2),
                charge_duration=round(duration_minutes, 2),
                start_time=start,
                end_time=end,
                total_charge_fee=round(total_charge_fee, 2),
                total_service_fee=round(total_service_fee_value, 2),
                total_fee=round(total_fee, 2),
                payment_status="UNPAID",
            )
            db.add(record)
            db.flush()

            for p in periods_result:
                detail = DetailedBill(
                    bill_id=bill_id,
                    period_name=p["period_name"],
                    period_start=p["period_start"],
                    period_end=p["period_end"],
                    period_duration=round(p["charge_kwh"] / rate_per_min, 2) if rate_per_min > 0 else 0,
                    period_charge_kwh=round(p["charge_kwh"], 2),
                    unit_price=p["unit_price"],
                    charge_fee=round(p["charge_fee"], 2),
                    service_fee=round(p["service_fee"], 2),
                    subtotal_fee=round(p["subtotal_fee"], 2),
                )
                db.add(detail)

            db.commit()

            logger.info(
                LogModule.BILLING,
                f"[计费] 账单生成成功 (bill_id: {bill_id}, session: {session_id}, "
                f"total: {total_fee:.2f})",
            )

            return {
                "success": True,
                "bill_id": bill_id,
                "session_id": session_id,
                "car_id": cs.car_id,
                "pile_id": cs.pile_id,
                "date": bill_date.isoformat(),
                "charge_amount_kwh": round(charged_kwh, 2),
                "charge_duration_minutes": round(duration_minutes, 2),
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "total_charge_fee": round(total_charge_fee, 2),
                "total_service_fee": round(total_service_fee_value, 2),
                "total_fee": round(total_fee, 2),
                "payment_status": "UNPAID",
                "periods": [
                    {
                        "period_name": p["period_name"],
                        "period_start": p["period_start"].isoformat(),
                        "period_end": p["period_end"].isoformat(),
                        "charge_kwh": round(p["charge_kwh"], 2),
                        "unit_price": p["unit_price"],
                        "charge_fee": round(p["charge_fee"], 2),
                        "service_fee": round(p["service_fee"], 2),
                        "subtotal_fee": round(p["subtotal_fee"], 2),
                    }
                    for p in periods_result
                ],
            }

        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ------------------------------------------------------------------
    # queryBillByDate: 按日期查询用户账单
    # ------------------------------------------------------------------
    def query_bill_by_date(self, car_id: str, date: str) -> list:
        """按日期查询账单

        Args:
            car_id: 车牌号
            date: 日期（YYYY-MM-DD）

        Returns:
            账单列表（可能为空数组）
        """
        db = get_session()
        try:
            if isinstance(date, str):
                query_date = datetime.strptime(date, "%Y-%m-%d").date()
            else:
                query_date = date

            records = (
                db.query(BillingRecord)
                .filter(
                    BillingRecord.car_id == car_id,
                    BillingRecord.date == query_date,
                )
                .order_by(BillingRecord.start_time.desc())
                .all()
            )

            return [
                {
                    "bill_id": r.bill_id,
                    "car_id": r.car_id,
                    "date": r.date.isoformat(),
                    "pile_id": r.pile_id,
                    "charge_amount": float(r.charge_amount),
                    "charge_duration_minutes": float(r.charge_duration),
                    "start_time": r.start_time.isoformat(),
                    "end_time": r.end_time.isoformat(),
                    "total_charge_fee": float(r.total_charge_fee),
                    "total_service_fee": float(r.total_service_fee),
                    "total_fee": float(r.total_fee),
                    "payment_status": r.payment_status,
                }
                for r in records
            ]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # getDetailedBill: 获取账单的时段级详单
    # ------------------------------------------------------------------
    def get_detailed_bill(self, bill_id: str) -> dict:
        """获取详单

        返回账单的分段明细，包括各时段的电费、服务费和小计。

        Args:
            bill_id: 账单编号

        Returns:
            {"bill_id": "...", "car_id": "...", "periods": [...]}
        """
        db = get_session()
        try:
            record = (
                db.query(BillingRecord)
                .filter(BillingRecord.bill_id == bill_id)
                .first()
            )

            if not record:
                return {
                    "bill_id": bill_id,
                    "car_id": "",
                    "date": "",
                    "pile_id": "",
                    "charge_amount": 0.0,
                    "charge_duration_minutes": 0.0,
                    "start_time": "",
                    "end_time": "",
                    "periods": [],
                }

            details = (
                db.query(DetailedBill)
                .filter(DetailedBill.bill_id == bill_id)
                .order_by(DetailedBill.period_start)
                .all()
            )

            periods = [
                {
                    "period_name": d.period_name,
                    "period_start": d.period_start.isoformat(),
                    "period_end": d.period_end.isoformat(),
                    "charge_kwh": float(d.period_charge_kwh),
                    "unit_price": float(d.unit_price),
                    "charge_fee": float(d.charge_fee),
                    "service_fee": float(d.service_fee),
                    "subtotal_fee": float(d.subtotal_fee),
                }
                for d in details
            ]

            return {
                "bill_id": record.bill_id,
                "car_id": record.car_id,
                "date": record.date.isoformat(),
                "pile_id": record.pile_id,
                "charge_amount": float(record.charge_amount),
                "charge_duration_minutes": float(record.charge_duration),
                "start_time": record.start_time.isoformat(),
                "end_time": record.end_time.isoformat(),
                "periods": periods,
                "payment_status": record.payment_status,
            }
        finally:
            db.close()
