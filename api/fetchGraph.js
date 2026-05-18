export async function fetchGraph() {
  const res = await fetch("http://localhost:5000/api/graph");
  return res.json();
}
