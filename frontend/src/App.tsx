import { useEffect, useState } from "react";
import type { Listing, Vertical } from "./api";
import { getListings } from "./api";

function App() {
  const [vertical, setVertical] = useState<Vertical>("car");
  const [listings, setListings] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    getListings({ vertical, limit: 50, offset: 0 })
      .then((page) => {
        setListings(page.items);
        setTotal(page.total);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load listings");
      })
      .finally(() => setLoading(false));
  }, [vertical]);

  return (
    <div>
      <h1>Blocky</h1>

      <select value={vertical} onChange={(e) => setVertical(e.target.value as Vertical)}>
        <option value="car">Cars</option>
        <option value="mc">Motorcycles</option>
      </select>

      {loading && <p>Loading…</p>}
      {error && <p>Error: {error}</p>}

      {!loading && !error && (
        <>
          <p>{total} listings</p>
          <table>
            <thead>
              <tr>
                <th>Make</th>
                <th>Model</th>
                <th>Year</th>
                <th>Price (SEK)</th>
                <th>Mileage (km)</th>
                <th>Location</th>
              </tr>
            </thead>
            <tbody>
              {listings.map((listing) => (
                <tr key={listing.id}>
                  <td>{listing.make}</td>
                  <td>{listing.model ?? "—"}</td>
                  <td>{listing.year}</td>
                  <td>{listing.price_sek ?? "—"}</td>
                  <td>{listing.mileage_km ?? "—"}</td>
                  <td>{listing.location}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

export default App;