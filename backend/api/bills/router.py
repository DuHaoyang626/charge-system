"""
账单模块路由占位
"""

from fastapi import APIRouter

router = APIRouter(tags=["账单"])


@router.get("/bills")
async def list_bills():
    """账单列表（待实现）"""
    return {"message": "list_bills - 待实现"}


@router.get("/bills/{bill_id}")
async def get_bill(bill_id: int):
    """账单详情（待实现）"""
    return {"message": f"get_bill {bill_id} - 待实现"}


@router.post("/bills/{bill_id}/pay")
async def pay_bill(bill_id: int):
    """支付账单（待实现）"""
    return {"message": f"pay_bill {bill_id} - 待实现"}
