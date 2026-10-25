interface RangeSliderProps {
  label: string;
  unit?: string;
  min: number;
  max: number;
  valueMin: number;
  valueMax: number;
  onChangeMin: (value: number) => void;
  onChangeMax: (value: number) => void;
}

function RangeSlider({
  label,
  unit = "",
  min,
  max,
  valueMin,
  valueMax,
  onChangeMin,
  onChangeMax,
}: RangeSliderProps) {
  const pctMin = ((valueMin - min) / (max - min)) * 100;
  const pctMax = ((valueMax - min) / (max - min)) * 100;

  return (
    <div className="range-slider-wrapper">
      <span>{label}: {valueMin}{unit} – {valueMax}{unit}</span>
      <div className="range-slider">
        <div className="range-slider-track-bg" />
        <div
          className="range-slider-track-fill"
          style={{ left: `${pctMin}%`, right: `${100 - pctMax}%` }}
        />
        <input
          type="range"
          min={min}
          max={max}
          value={valueMin}
          onChange={(e) => onChangeMin(Math.min(Number(e.target.value), valueMax))}
        />
        <input
          type="range"
          min={min}
          max={max}
          value={valueMax}
          onChange={(e) => onChangeMax(Math.max(Number(e.target.value), valueMin))}
        />
      </div>
    </div>
  );
}

export default RangeSlider;
