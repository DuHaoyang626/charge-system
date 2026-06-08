"""
支付服务 — PaymentService

职责：模拟支付流程，更新账单状态
"""

from datetime import datetime

from src.db.database import get_session
from src.db.models import BillingRecord, PaymentOrder
from src.enums import LogModule
from src.utils.logger import logger


class PaymentService:
    """支付服务"""

    def pay_bill(self, bill_id: str) -> dict:
        """支付账单

        将指定账单的 payment_status 更新为 PAID，
        同时创建支付订单记录。

        Args:
            bill_id: 账单编号

        Returns:
            成功: {"success": True, "bill_id": "...", "payment_status": "PAID"}
            失败: {"success": False, "message": "账单不存在"} 等
        """
        session = get_session()
        try:
            bill = session.query(BillingRecord).filter(
                BillingRecord.bill_id == bill_id
            ).first()

            if not bill:
                return {"success": False, "message": "账单不存在"}

            if bill.payment_status == "PAID":
                return {"success": True, "bill_id": bill_id,
                        "payment_status": "PAID", "message": "账单已支付"}

            now = datetime.now()
            # 更新账单状态
            bill.payment_status = "PAID"
            bill.updated_at = now

            # 创建支付订单
            order_id = f"P{now.strftime('%Y%m%d%H%M%S%f')}"
            order = PaymentOrder(
                order_id=order_id,
                bill_id=bill_id,
                car_id=bill.car_id,
                total_amount=bill.total_fee,
                payment_status="PAID",
                payment_method="MOCK",
                payment_time=now,
                created_at=now,
                updated_at=now,
            )
            session.add(order)
            session.commit()

            logger.info(LogModule.BILLING,
                        f"[支付] 账单 {bill_id} 支付成功 (金额: {bill.total_fee})")
            return {
                "success": True,
                "bill_id": bill_id,
                "payment_status": "PAID",
                "order_id": order_id,
                "total_amount": float(bill.total_fee),
            }

        except Exception as e:
            session.rollback()
            logger.error(LogModule.BILLING,
                         f"[支付] 账单 {bill_id} 支付失败: {e}")
            return {"success": False, "message": f"支付失败: {e}"}
        finally:
            session.close()
