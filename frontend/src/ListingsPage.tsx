import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import type { Listing, SortField, SortOrder, Vertical } from "./api";
import { getListings, getMakes } from "./api";
import { Link } from "react-router-dom";
import RangeSlider from "./RangeSlider";
import "./App.css"

export const PRICE_BOUNDS: Record<Vertical, { min: number; max: number }> = {
  car: { min: 0, max: 50000 },
  mc: { min: 0, max: 50000 },
};
export const YEAR_MIN = 1990;
export const YEAR_MAX = new Date().getFullYear();

export interface Filters {
  priceMin: number;
  priceMax: number;
  make: string[];
  yearMin: number;
  yearMax: number;
}

export function defaultFilters(vertical: Vertical): Filters {
  const bounds = PRICE_BOUNDS[vertical];
  return {
    priceMin: bounds.min,
    priceMax: bounds.max,
    make: [],
    yearMin: YEAR_MIN,
    yearMax: YEAR_MAX,
  };
}

interface ListingsPageProps {
  vertical: Vertical;
  setVertical: (vertical: Vertical) => void;
  filters: Filters;
  setFilters: (filters: Filters) => void;
  offset: number;
  setOffset: Dispatch<SetStateAction<number>>;
  sort: SortField;
  setSort: (sort: SortField) => void;
  order: SortOrder;
  setOrder: (order: SortOrder) => void;
}

function ListingsPage({
  vertical, setVertical,
  filters, setFilters,
  offset, setOffset,
  sort, setSort,
  order, setOrder,
}: ListingsPageProps) {
  const [priceMin, setPriceMin] = useState(filters.priceMin);
  const [priceMax, setPriceMax] = useState(filters.priceMax);
  const [make, setMake] = useState(filters.make);
  const [yearMin, setYearMin] = useState(filters.yearMin);
  const [yearMax, setYearMax] = useState(filters.yearMax);

  const limit = 50;

  const [makes, setMakes] = useState<string[]>([]);
  const [makesError, setMakesError] = useState<string | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMakesError(null);
    getMakes(vertical)
      .then(setMakes)
      .catch((err: unknown) => {
        setMakes([]);
        setMakesError(err instanceof Error ? err.message : "Failed to load makes");
      });
  }, [vertical]);

  useEffect(() => {
    setLoading(true);
    setError(null);

    getListings({
      vertical,
      limit,
      offset,
      sort,
      order,
      price_min: filters.priceMin,
      price_max: filters.priceMax,
      make: filters.make.length ? filters.make : undefined,
      year_min: filters.yearMin,
      year_max: filters.yearMax,
     })
      .then((page) => {
        setListings(page.items);
        setTotal(page.total);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load listings");
      })
      .finally(() => setLoading(false));
  }, [vertical, filters, offset, sort, order]);

  function applyFilters(){
    setOffset(0);
    setFilters({priceMin, priceMax, make, yearMin, yearMax})
  }

  function resetFilters() {
    const defaults = defaultFilters(vertical);
    setPriceMin(defaults.priceMin);
    setPriceMax(defaults.priceMax);
    setMake(defaults.make);
    setYearMin(defaults.yearMin);
    setYearMax(defaults.yearMax);
    setOffset(0);
    setFilters(defaults);
  }

  function toggleMake(m: string) {
    setMake((prev) =>
      prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m]
    );
  }

  function toggleSort(field: SortField) {
    setOffset(0);
    if (sort === field) {
      setOrder(order === "asc" ? "desc" : "asc");
    } else {
      setSort(field);
      setOrder("asc");
    }
  }

  function sortArrow(field: SortField) {
    if (sort !== field) return null;
    return order === "asc" ? " ▲" : " ▼";
  }

  const page = Math.floor(offset/limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total/limit));
  return (
    <div className="app">
      <h1>Blocky</h1>

      <div className="toolbar">
        <select
          value={vertical}
          onChange={(e) => {
            const v = e.target.value as Vertical;
            const defaults = defaultFilters(v);
            setOffset(0);
            setVertical(v);
            setPriceMin(defaults.priceMin);
            setPriceMax(defaults.priceMax);
            setMake(defaults.make);
            setYearMin(defaults.yearMin);
            setYearMax(defaults.yearMax);
            setFilters(defaults);
          }}>
            <option value="car">Cars</option>
            <option value="mc">Motorcycles</option>
        </select>
      </div>

      <div className="filters">
        <div className="make-filter">
          <span>Makes{make.length > 0 ? ` (${make.length} selected)` : ""}</span>
          <div className="make-grid">
            {makes.map((m) => (
              <button
                key={m}
                type="button"
                className={make.includes(m) ? "make-pill selected" : "make-pill"}
                onClick={() => toggleMake(m)}
              >
                {m}
              </button>
            ))}
          </div>
          {makesError && <span className="filters-error">Couldn't load makes: {makesError}</span>}
        </div>

        <RangeSlider
          label="Price"
          unit=" kr"
          min={PRICE_BOUNDS[vertical].min}
          max={PRICE_BOUNDS[vertical].max}
          valueMin={priceMin}
          valueMax={priceMax}
          onChangeMin={setPriceMin}
          onChangeMax={setPriceMax}
        />

        <RangeSlider
          label="Year"
          min={YEAR_MIN}
          max={YEAR_MAX}
          valueMin={yearMin}
          valueMax={yearMax}
          onChangeMin={setYearMin}
          onChangeMax={setYearMax}
        />

        <button className="btn-primary" onClick={applyFilters}>Apply</button>
        <button onClick={resetFilters}>Reset filters</button>
      </div>

      {loading && <p>Loading…</p>}
      {error && <p>Error: {error}</p>}

      {!loading && !error && (
        <>
         <div className="pagination">
            <button onClick={() => setOffset((o) => Math.max(0, o-limit))} disabled={offset === 0}>
              Previous
            </button>
            <span>Page {page} of {pageCount}</span>
            <button onClick={() => setOffset((o) => o+limit)} disabled={offset + limit >= total}>
              Next
            </button>
          </div>
          <p>{total} listings</p>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Make</th>
                  <th>Model</th>
                  <th className="sortable" onClick={() => toggleSort("year")}>Year{sortArrow("year")}</th>
                  <th className="sortable" onClick={() => toggleSort("price")}>Price (SEK){sortArrow("price")}</th>
                  <th className="sortable" onClick={() => toggleSort("mileage")}>Mileage (km){sortArrow("mileage")}</th>
                  <th>Location</th>
                </tr>
              </thead>
              <tbody>
                {listings.map((listing) => (
                  <tr key={listing.id}>
                  <td><Link to={`/listings/${listing.id}`}>{listing.make}</Link></td>
                    <td>{listing.model ?? "—"}</td>
                    <td>{listing.year}</td>
                    <td>{listing.price_sek ?? "—"}</td>
                    <td>{listing.mileage_km ?? "—"}</td>
                    <td>{listing.location}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button onClick={() => setOffset((o) => Math.max(0, o-limit))} disabled={offset === 0}>
              Previous
            </button>
            <span>Page {page} of {pageCount}</span>
            <button onClick={() => setOffset((o) => o+limit)} disabled={offset + limit >= total}>
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default ListingsPage;
