export function isEmail(value: string): boolean {
  return /^\S+@\S+\.\S+$/.test(value.trim())
}
