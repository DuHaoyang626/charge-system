"""
计费引擎 — 纯函数，不依赖数据库/请求上下文。

电费：按充电时间比例将总充电量分配到各电价时段，Σ(时段电量 × 电价)
服务费：基础服务费 + Σ(各阶梯分钟数 × 阶梯费率)
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta


BJT_OFFSET = timedelta(hours=8)


@dataclass
class FeeItem:
    name: str
    quantity: float      # 电量(kWh) / 分钟数
    unit_price: float    # 电价 / 费率
    fee: float


@dataclass
class FeeResult:
    items: list[FeeItem] = field(default_factory=list)
    total: float = 0.0


@dataclass
class PriceSlot:
    """电价时段"""
    period_name: str
    start_time: str      # HH:mm (北京时间)
    end_time: str        # HH:mm (北京时间)
    price_per_kwh: float


@dataclass
class ServiceTier:
    """服务费阶梯"""
    tier_name: str
    min_minutes: int
    max_minutes: int | None   # None = 无上限
    rate_per_minute: float


def _utc_to_bjt(dt: datetime) -> datetime:
    """UTC → 北京时间"""
    return dt + BJT_OFFSET


def _minutes_since_midnight(dt: datetime) -> int:
    """返回北京时间当天从 00:00 开始的分钟数"""
    return dt.hour * 60 + dt.minute


def _time_str_to_minutes(t: str) -> int:
    """将 'HH:MM' 转为当天分钟数"""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _slice_time_range(
    start_bjt: datetime,
    end_bjt: datetime,
    prices: list[PriceSlot],
) -> list[tuple[PriceSlot, float]]:
    """将 [start, end) 时间区间按电价时段切片，返回 [(时段, 分钟数), ...]。"""
    start_min = _minutes_since_midnight(start_bjt)
    end_min = _minutes_since_midnight(end_bjt)
    total_duration = (end_bjt - start_bjt).total_seconds() / 60.0

    # 处理跨天：如果结束时间 < 开始时间，说明跨天，拆分成两段
    if end_bjt.date() > start_bjt.date():
        # 第一段：start → 当天午夜
        midnight = start_bjt.replace(hour=23, minute=59, second=59, microsecond=999999)
        seg1_minutes = (midnight - start_bjt).total_seconds() / 60.0
        seg2_minutes = total_duration - seg1_minutes

        # 递归处理两段
        results = _slice_time_range_in_day(start_bjt, midnight, prices)
        next_day_start = start_bjt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        results2 = _slice_time_range_in_day(next_day_start, end_bjt, prices)
        return results + results2
    else:
        return _slice_time_range_in_day(start_bjt, end_bjt, prices)


def _slice_time_range_in_day(
    start_bjt: datetime,
    end_bjt: datetime,
    prices: list[PriceSlot],
) -> list[tuple[PriceSlot, float]]:
    """同一天内的时间切片。"""
    start_min = _minutes_since_midnight(start_bjt)
    end_min = _minutes_since_midnight(end_bjt)
    results: list[tuple[PriceSlot, float]] = []

    for p in sorted(prices, key=lambda x: _time_str_to_minutes(x.start_time)):
        ps = _time_str_to_minutes(p.start_time)
        pe = _time_str_to_minutes(p.end_time)

        if pe <= ps:
            pe += 1440  # 跨天时段（如 21:00 → 08:00）

        seg_start = max(start_min, ps)
        seg_end = min(end_min, pe)

        if seg_start < seg_end:
            minutes = seg_end - seg_start
            results.append((p, minutes))

    return results


def calculate_electricity_fee(
    start_time: datetime,
    end_time: datetime,
    total_energy_kwh: float,
    prices: list[PriceSlot],
) -> FeeResult:
    """
    计算电费。

    将总充电量按各时段分钟数比例分配到各电价时段。
    start_time / end_time 为 UTC datetime。
    prices 为电价时段列表（北京时间）。
    """
    start_bjt = _utc_to_bjt(start_time)
    end_bjt = _utc_to_bjt(end_time)
    total_minutes = max(1, (end_bjt - start_bjt).total_seconds() / 60.0)

    slices = _slice_time_range(start_bjt, end_bjt, prices)

    result = FeeResult()
    for i, (p, minutes) in enumerate(slices):
        ratio = minutes / total_minutes
        if i < len(slices) - 1:
            energy = round(total_energy_kwh * ratio, 4)
        else:
            # 末时段：用差值确保 Σenergy == total_energy_kwh，消除 round 累加误差
            used = sum(item.quantity for item in result.items)
            energy = round(total_energy_kwh - used, 4)
        fee = round(energy * p.price_per_kwh, 2)
        result.items.append(FeeItem(
            name=p.period_name,
            quantity=energy,
            unit_price=p.price_per_kwh,
            fee=fee,
        ))
        result.total += fee

    result.total = round(result.total, 2)
    return result


def calculate_service_fee(
    charging_minutes: int,
    base_fee: float,
    tiers: list[ServiceTier],
) -> FeeResult:
    """
    计算服务费。

    基础服务费固定 + 阶梯费率按分钟数累加。
    """
    result = FeeResult()
    remaining = charging_minutes

    # 基础服务费
    result.items.append(FeeItem(
        name="基础服务费",
        quantity=1,
        unit_price=base_fee,
        fee=base_fee,
    ))
    result.total += base_fee

    # 阶梯费率
    for t in sorted(tiers, key=lambda x: x.min_minutes):
        if remaining <= 0:
            break
        if t.max_minutes is not None:
            tier_minutes = min(remaining, t.max_minutes - t.min_minutes)
        else:
            tier_minutes = remaining

        tier_minutes = max(0, tier_minutes)
        if tier_minutes <= 0:
            continue

        fee = round(tier_minutes * t.rate_per_minute, 2)
        result.items.append(FeeItem(
            name=t.tier_name or f"{t.min_minutes}-{t.max_minutes or '∞'}分钟",
            quantity=tier_minutes,
            unit_price=t.rate_per_minute,
            fee=fee,
        ))
        result.total += fee
        remaining -= tier_minutes

    result.total = round(result.total, 2)
    return result
