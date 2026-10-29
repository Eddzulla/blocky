import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import type { Listing } from "./api";
import { getListing } from "./api";

function ListingDetail() {
  const { id } = useParams<{ id: string }>();
  const [listing, setListing] = useState<Listing | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getListing(Number(id))
      .then(setListing)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load listing");
      });
  }, [id]);

  if (error) return <p>Error: {error}</p>;
  if (!listing) return <p>Loading…</p>;

  return (
    <div className="detail">
      <Link to="/">← Back to listings</Link>

      {listing.image_urls.length > 0 && (
        <div className="detail-gallery">
          {listing.image_urls.slice(0, 6).map((src) => (
            <img key={src} src={src} alt={`${listing.make} ${listing.model ?? ""}`} />
          ))}
        </div>
      )}

      <h1>{listing.make} {listing.model ?? ""}</h1>
      <p>{listing.model_specification}</p>
      <p>Year: {listing.year}</p>
      <p>Price: {listing.price_sek ?? "—"} SEK</p>
      <p>Mileage: {listing.mileage_km ?? "—"} km</p>
      {listing.engine_cc !== null && <p>Engine: {listing.engine_cc} cc</p>}
      <p>Location: {listing.location}</p>
      <a className="btn-primary btn-link" href={listing.url} target="_blank" rel="noreferrer">View on Blocket</a>
    </div>
  );
}

export default ListingDetail;
