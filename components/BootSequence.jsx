import { useEffect, useState } from "react";
const lines = [
  "Initializing graph topology...",
  "Loading transaction matrices...",
  "Computing anomaly clusters...",
  "Propagating risk vectors...",
  "MuleNetX online"
];
export default function BootSequence() {
  const [visible, setVisible] = useState([]);
  useEffect(() => {
    lines.forEach((line, index) => {
      setTimeout(() => {
        setVisible(v => [...v, line]);
      }, index * 900);
    });
  }, []);
  return (
    <div>
      {visible.map((line, i) => (
        <div key={i}>{line}</div>
      ))}
    </div>
  );
}
