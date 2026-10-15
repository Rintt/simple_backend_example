export function format(value) {
  return Number(value).toLocaleString(undefined, { maximumSignificantDigits: 6 })
}
