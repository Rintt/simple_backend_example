// A fieldset of checkboxes; the selection keeps the order of `options`
export default function CheckboxGroup({ legend, options, selected, onChange }) {
  function toggle(item) {
    const next = selected.includes(item) ? selected.filter((x) => x !== item) : [...selected, item]
    onChange(options.filter((x) => next.includes(x)))
  }

  return (
    <fieldset>
      <legend>{legend}</legend>
      {options.map((option) => (
        <label key={option} className="check">
          <input type="checkbox" checked={selected.includes(option)} onChange={() => toggle(option)} />
          {option}
        </label>
      ))}
    </fieldset>
  )
}
