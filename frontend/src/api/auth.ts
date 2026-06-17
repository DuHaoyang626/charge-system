/**
 * 认证模块 API
 */

import api from './request'

export interface RegisterRequest {
  licensePlate: string
  userName: string
  batteryCapacity: number
  password: string
  confirmPassword: string
  protocolIds: number[]
  phone?: string
}

export interface RegisterResponse {
  userId: number
  licensePlate: string
  userName: string
  token: string
}

export function registerApi(data: RegisterRequest) {
  return api.post('/auth/register', data)
}

export interface LoginRequest {
  licensePlate: string
  password: string
}

export interface LoginResponse {
  userId: number
  licensePlate: string
  userName: string
  token: string
  role: string
}

export function loginApi(data: LoginRequest) {
  return api.post('/auth/login', data)
}

/** 用户信息（GET /users/me） */
export interface ProtocolInfo {
  id: number
  name: string
  powerKw: number
}

export interface ActiveSession {
  sessionId: number
  status: string
  stationName: string
  progress: number
}

export interface UserInfo {
  userId: number
  licensePlate: string
  userName: string
  phone: string | null
  batteryCapacity: number
  protocols: ProtocolInfo[]
  activeSession: ActiveSession | null
}

export function getUserInfoApi() {
  return api.get('/users/me')
}

/** 获取所有协议（用于注册页选择） */
export interface ProtocolOption {
  id: number
  name: string
  powerKw: number
}

export function getProtocolsApi() {
  return api.get('/protocols')
}
