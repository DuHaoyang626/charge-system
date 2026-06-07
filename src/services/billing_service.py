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

from typing import Optional


class BillingService:
    """充电计费服务"""

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
            {"success": True, "bill_id": "B20260607001",
             "total_charge_fee": 45.6,       # 电费合计
             "total_service_fee": 12.5,      # 服务费合计
             "total_fee": 58.1,              # 总费用
             "periods": [...]}               # 各时段明细

        Examples:
            >>> bs = BillingService()
            >>> bs.calculate_bill("S20260607001")
            {"success": True, "bill_id": "B20260607001", ...}
        """
        # TODO: 真实实现
        # 1. 查询充电会话 SELECT * FROM charging_sessions WHERE session_id=?
        # 2. 获取该充电桩的计费规则（pile_tariff_configs 表 或 配置默认值）
        # 3. 按充电时间跨越的时段分段：
        #    - 遍历从 start_time 到 end_time 的每一分钟
        #    - 判断每分钟所属时段（peak/normal/valley）
        #    - 累计各时段的充电量（按功率积分或均匀分配）
        # 4. 电费 = Σ(时段充电量 × 对应电价)
        # 5. 服务费 = base_service_fee + time_coefficient × duration_minutes
        # 6. 写入 billing_records 表 + detailed_bills 表
        # 7. logger.info("BILLING", f"[计费] 账单生成成功 (bill_id: {bill_id}, total: {total_fee})")
        # 8. return {"success": True, "bill_id": bill_id, ...}
        return {
            "success": True,
            "bill_id": "B20260607001",
            "session_id": session_id,
            "charge_amount_kwh": 45.5,
            "charge_duration_minutes": 60.0,
            "total_charge_fee": 45.6,
            "total_service_fee": 12.5,
            "total_fee": 58.1,
            "periods": [
                {
                    "period_name": "peak",
                    "charge_kwh": 20.0,
                    "unit_price": 1.2,
                    "charge_fee": 24.0,
                    "service_fee": 5.0,
                    "subtotal_fee": 29.0,
                },
                {
                    "period_name": "normal",
                    "charge_kwh": 25.5,
                    "unit_price": 0.8,
                    "charge_fee": 20.4,
                    "service_fee": 7.5,
                    "subtotal_fee": 27.9,
                },
            ],
        }

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
            [{"bill_id": "B20260607001", "date": "2026-06-07",
              "charge_amount": 45.5, "total_fee": 58.1, ...}, ...]

        Examples:
            >>> bs.query_bill_by_date("京A12345", "2026-06-07")
            [{"bill_id": "B20260607001", ...}]
        """
        # TODO: 真实实现
        # SELECT * FROM billing_records WHERE car_id=? AND date=? ORDER BY start_time DESC
        return [
            {
                "bill_id": "B20260607001",
                "car_id": car_id,
                "date": date,
                "pile_id": "P001",
                "charge_amount": 45.5,
                "charge_duration_minutes": 60.0,
                "start_time": "2026-06-07T10:30:00",
                "end_time": "2026-06-07T11:30:00",
                "total_charge_fee": 45.6,
                "total_service_fee": 12.5,
                "total_fee": 58.1,
                "payment_status": "UNPAID",
            }
        ]

    # ------------------------------------------------------------------
    # getDetailedBill: 获取账单的时段级详单
    # ------------------------------------------------------------------
    def get_detailed_bill(self, bill_id: str) -> dict:
        """获取详单

        返回账单的分段明细，包括各时段的电费、服务费和小计。

        Args:
            bill_id: 账单编号

        Returns:
            {"bill_id": "B20260607001", "car_id": "京A12345",
             "periods": [{"period_name": "peak", ...}, ...]}

        Examples:
            >>> bs.get_detailed_bill("B20260607001")
            {"bill_id": "B20260607001", ...}
        """
        # TODO: 真实实现
        # SELECT * FROM detailed_bills WHERE bill_id=? ORDER BY period_start
        return {
            "bill_id": bill_id,
            "car_id": "京A12345",
            "date": "2026-06-07",
            "pile_id": "P001",
            "charge_amount": 45.5,
            "charge_duration_minutes": 60.0,
            "start_time": "2026-06-07T10:30:00",
            "end_time": "2026-06-07T11:30:00",
            "periods": [
                {
                    "period_name": "peak",
                    "period_start": "2026-06-07T10:30:00",
                    "period_end": "2026-06-07T11:00:00",
                    "charge_kwh": 20.0,
                    "unit_price": 1.2,
                    "charge_fee": 24.0,
                    "service_fee": 5.0,
                    "subtotal_fee": 29.0,
                },
                {
                    "period_name": "normal",
                    "period_start": "2026-06-07T11:00:00",
                    "period_end": "2026-06-07T11:30:00",
                    "charge_kwh": 25.5,
                    "unit_price": 0.8,
                    "charge_fee": 20.4,
                    "service_fee": 7.5,
                    "subtotal_fee": 27.9,
                },
            ],
        }
