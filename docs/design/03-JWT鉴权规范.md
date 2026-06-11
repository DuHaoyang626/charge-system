# JWT 鉴权规范

> 本文档定义本系统的 JWT Token 结构、签发与验签规则。
> **目标**：无论 Python/FastAPI 还是 Java/Spring Boot 接入，使用同一套密钥和算法即可互认。

---

## 一、Token 规格

| 项目 | 值 |
|------|----|
| **算法** | HS256（HMAC-SHA256） |
| **密钥类型** | 对称密钥（双方配置相同 secret） |
| **密钥长度** | ≥ 32 字符 |
| **有效期** | 24 小时 |
| **编码** | Base64url |

---

## 二、Header

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

固定值，所有 Token 一致。

---

## 三、Payload（Claims）

| 字段 | 类型 | 必含 | 说明 |
|------|------|------|------|
| `user_id` | int | 是 | 用户 ID。**注意**：字段名为 `user_id`，不是 `userId` 或 `sub` |
| `role` | string | 是 | 角色：`user`（普通用户）或 `admin`（管理员） |
| `exp` | int | 是 | 过期时间，Unix 时间戳（秒） |
| `iat` | int | 否 | 签发时间，Unix 时间戳（秒） |

### 示例 Payload（解码后）

```json
{
  "user_id": 1,
  "role": "user",
  "exp": 1778515200,
  "iat": 1778428800
}
```

---

## 四、Token 示例（完整 JWT）

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJyb2xlIjoidXNlciIsImV4cCI6MTc3ODUxNTIwMCwiaWF0IjoxNzc4NDI4ODAwfQ.abcdef1234567890signature
```

三部分：
```
Header                            Payload                                                                         Signature
```

---

## 五、Python 实现（本系统用）

### 5.1 配置

```python
# core/config.py
JWT_SECRET_KEY = "your-32-char-minimum-secret-key-here"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 1
```

> **注意**：`JWT_SECRET_KEY` 必须从环境变量读取，不硬编码。
> 生产环境：`export JWT_SECRET_KEY="xxx"`
> 开发环境：项目根目录 `.env` 文件。

### 5.2 签发 Token

```python
# core/security.py
from datetime import datetime, timedelta
from jose import jwt

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
EXPIRE_DAYS = 1

def create_access_token(user_id: int, role: str = "user") -> str:
    """签发 JWT Token"""
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": int((datetime.utcnow() + timedelta(days=EXPIRE_DAYS)).timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
```

### 5.3 验签 & 解析

```python
# core/security.py
from jose import JWTError, jwt

def verify_token(token: str) -> dict | None:
    """验证 Token，成功返回 payload，失败返回 None"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_user_id(token: str) -> int | None:
    """从 Token 中提取 user_id"""
    payload = verify_token(token)
    if payload is None:
        return None
    return payload.get("user_id")
```

### 5.4 FastAPI 依赖注入

```python
# core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.security import verify_token

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """从请求头 Authorization: Bearer <token> 中提取 user_id"""
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return payload.get("user_id")

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """管理员鉴权，比 get_current_user 多校验 role=admin"""
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None or payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return payload.get("user_id")
```

### 5.5 在 API 中使用

```python
# api/sessions/router.py
from fastapi import APIRouter, Depends
from core.deps import get_current_user

router = APIRouter()

@router.post("/sessions")
async def create_session(
    body: SessionCreate,
    user_id: int = Depends(get_current_user),   # ← 从 Token 获取
):
    # user_id 已就绪，直接使用
    return await session_service.create(user_id, body)
```

```python
# api/admin/config/router.py
from fastapi import APIRouter, Depends
from core.deps import get_current_admin

router = APIRouter()

@router.put("/admin/config")
async def update_config(
    body: ConfigUpdate,
    admin_id: int = Depends(get_current_admin),  # ← 仅管理员可访问
):
    return await config_service.update(body)
```

---

## 六、Java 实现（供其他项目参考）

### 6.1 依赖（Maven）

```xml
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-api</artifactId>
    <version>0.12.5</version>
</dependency>
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-impl</artifactId>
    <version>0.12.5</version>
    <scope>runtime</scope>
</dependency>
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-jackson</artifactId>
    <version>0.12.5</version>
    <scope>runtime</scope>
</dependency>
```

### 6.2 签发 Token

```java
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

public class JwtUtil {
    private static final String SECRET = "your-32-char-minimum-secret-key-here";
    private static final SecretKey KEY = Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8));
    private static final long EXPIRE_MS = 24 * 60 * 60 * 1000L;

    public static String createToken(Integer userId, String role) {
        return Jwts.builder()
            .claim("user_id", userId)
            .claim("role", role)
            .issuedAt(new Date())
            .expiration(new Date(System.currentTimeMillis() + EXPIRE_MS))
            .signWith(KEY)
            .compact();
    }
}
```

### 6.3 验签 & 解析

```java
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;

public class JwtUtil {
    public static Claims verifyToken(String token) {
        try {
            return Jwts.parser()
                .verifyWith(KEY)
                .build()
                .parseSignedClaims(token)
                .getPayload();
        } catch (JwtException e) {
            return null;
        }
    }

    public static Integer getUserId(String token) {
        Claims claims = verifyToken(token);
        return claims != null ? claims.get("user_id", Integer.class) : null;
    }

    public static String getRole(String token) {
        Claims claims = verifyToken(token);
        return claims != null ? claims.get("role", String.class) : null;
    }
}
```

### 6.4 Spring Boot 拦截器

```java
@Component
public class JwtInterceptor implements HandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String auth = request.getHeader("Authorization");
        if (auth == null || !auth.startsWith("Bearer ")) {
            response.setStatus(401);
            return false;
        }
        String token = auth.substring(7);
        Integer userId = JwtUtil.getUserId(token);
        if (userId == null) {
            response.setStatus(401);
            return false;
        }
        request.setAttribute("userId", userId);
        return true;
    }
}
```

---

## 七、跨语言互认检查清单

| 检查项 | Python | Java | 说明 |
|--------|--------|------|------|
| 算法 | `HS256` | `HS256` | 一致 |
| 密钥 | `jwt.encode(payload, key, algorithm)` | `Keys.hmacShaKeyFor(secret.getBytes())` | 同一字符串密钥 |
| claims 字段名 | `user_id` | `"user_id"` | **必须一致**，不能用 `sub` 或 `userId` |
| user_id 类型 | `int` | `Integer` | 一致 |
| role 值 | `"user"` / `"admin"` | `"user"` / `"admin"` | 一致 |
| exp 单位 | Unix 秒（`timestamp()`） | `System.currentTimeMillis() + EXPIRE_MS` | 需注意 Java 的 `expiration` 也是秒级（jjwt 自动转） |
| Header | `{"alg":"HS256","typ":"JWT"}` | 自动生成 | 一致 |

---

## 八、安全注意事项

| 要求 | 说明 |
|------|------|
| **密钥隔离** | 开发/测试/生产使用不同的 secret_key |
| **HTTPS** | 生产环境必须 HTTPS，防止 Token 被截获 |
| **短期 Token** | 24 小时过期，前端过期后应跳转登录页刷新 |
| **不在 Payload 存敏感信息** | 不存密码、手机号等，只存 user_id 和 role |

---

> 文档版本：v1.0 | 2026-06-09
