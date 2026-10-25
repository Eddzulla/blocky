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
export const MILEAGE_BOUNDS: Record<Vertical, { min: number; max: number }> = {
  car: { min: 0, max: 500000 },
  mc: { min: 0, max: 150000 },
};
export const YEAR_MIN = 1990;
export const YEAR_MAX = new Date().getFullYear();

export interface Filters {
  priceMin: number;
  priceMax: number;
  mileageMin: number;
  mileageMax: number;
  make: string[];
  search: string;
  yearMin: number;
  yearMax: number;
}

export function defaultFilters(vertical: Vertical): Filters {
  const bounds = PRICE_BOUNDS[vertical];
  const mileageBounds = MILEAGE_BOUNDS[vertical];
  return {
    priceMin: bounds.min,
    priceMax: bounds.max,
    mileageMin: mileageBounds.min,
    mileageMax: mileageBounds.max,
    make: [],
    search: "",
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
  const [mileageMin, setMileageMin] = useState(filters.mileageMin);
  const [mileageMax, setMileageMax] = useState(filters.mileageMax);
  const [make, setMake] = useState(filters.make);
  const [search, setSearch] = useState(filters.search);
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
      mileage_min: filters.mileageMin,
      mileage_max: filters.mileageMax,
      make: filters.make.length ? filters.make : undefined,
      search: filters.search.trim() || undefined,
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
    setFilters({priceMin, priceMax, mileageMin, mileageMax, make, search, yearMin, yearMax})
  }

  function resetFilters() {
    const defaults = defaultFilters(vertical);
    setPriceMin(defaults.priceMin);
    setPriceMax(defaults.priceMax);
    setMileageMin(defaults.mileageMin);
    setMileageMax(defaults.mileageMax);
    setMake(defaults.make);
    setSearch(defaults.search);
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
      <h2>- för dig som vill skambuda på en shkruttig liten kärra</h2>

      <div className="toolbar">
        <select
          value={vertical}
          onChange={(e) => {
            const v = e.target.value as Vertical;
            const defaults = defaultFilters(v);
            setOffset(0);
            setVertical(v);
            if (v === "car" && sort === "engine_cc") {
              setSort("last_seen");
              setOrder("desc");
            }
            setPriceMin(defaults.priceMin);
            setPriceMax(defaults.priceMax);
            setMileageMin(defaults.mileageMin);
            setMileageMax(defaults.mileageMax);
            setMake(defaults.make);
            setSearch(defaults.search);
            setYearMin(defaults.yearMin);
            setYearMax(defaults.yearMax);
            setFilters(defaults);
          }}>
            <option value="car">Cars</option>
            <option value="mc">Motorcycles</option>
        </select>
      </div>

      <div className="filters">
        <input
          type="text"
          className="search-input"
          placeholder="Search make or model (e.g. Honda Civic)"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") applyFilters(); }}
        />

        <div className="facet-filter">
          <span>Makes{make.length > 0 ? ` (${make.length} selected)` : ""}</span>
          <div className="facet-grid">
            {makes.map((m) => (
              <button
                key={m}
                type="button"
                className={make.includes(m) ? "facet-pill selected" : "facet-pill"}
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
          label="Mileage"
          unit=" km"
          min={MILEAGE_BOUNDS[vertical].min}
          max={MILEAGE_BOUNDS[vertical].max}
          valueMin={mileageMin}
          valueMax={mileageMax}
          onChangeMin={setMileageMin}
          onChangeMax={setMileageMax}
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
                  <th>Image</th>
                  <th className="sortable" onClick={() => toggleSort("make")}>Make{sortArrow("make")}</th>
                  <th className="sortable" onClick={() => toggleSort("model")}>Model{sortArrow("model")}</th>
                  <th className="sortable" onClick={() => toggleSort("year")}>Year{sortArrow("year")}</th>
                  <th className="sortable" onClick={() => toggleSort("price")}>Price (SEK){sortArrow("price")}</th>
                  <th className="sortable" onClick={() => toggleSort("mileage")}>Mileage (km){sortArrow("mileage")}</th>
                  {vertical === "mc" && (
                    <th className="sortable" onClick={() => toggleSort("engine_cc")}>Engine (cc){sortArrow("engine_cc")}</th>
                  )}
                  <th>Location</th>
                </tr>
              </thead>
              <tbody>
                {listings.map((listing) => (
                  <tr key={listing.id}>
                    <td>
                      {listing.image_urls[0] && (
                        <Link to={`/listings/${listing.id}`}>
                          <img className="thumbnail" src={listing.image_urls[0]} alt={`${listing.make} ${listing.model ?? ""}`} />
                        </Link>
                      )}
                    </td>
                  <td><Link to={`/listings/${listing.id}`}>{listing.make}</Link></td>
                    <td>{listing.model ?? "—"}</td>
                    <td>{listing.year}</td>
                    <td>{listing.price_sek ?? "—"}</td>
                    <td>{listing.mileage_km ?? "—"}</td>
                    {vertical === "mc" && <td>{listing.engine_cc ?? "—"}</td>}
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
