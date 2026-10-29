import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import type { SortField, SortOrder, Vertical, Status } from "./api";
import { getStatus } from "./api";
import ListingsPage, { defaultFilters } from "./ListingsPage";
import ListingDetail from "./ListingDetail";

function App() {
  const [vertical, setVertical] = useState<Vertical>("car");
  const [filters, setFilters] = useState(defaultFilters("car"));
  const [offset, setOffset] = useState(0);
  const [sort, setSort] = useState<SortField>("last_seen");
  const [order, setOrder] = useState<SortOrder>("desc");
  const [status, setStatus] = useState<Status | null>(null);
  useEffect(() => { getStatus().then(setStatus).catch(() => {}); }, []);

  return (
    <BrowserRouter>
      {status && (
      <p className="refresh-status">
        Full fetch: {status.full_fetch_at ? new Date(status.full_fetch_at).toLocaleString() : "never"}
        <br></br>
        Quick fetch: {status.quick_fetch_at ? new Date(status.quick_fetch_at).toLocaleString() : "never"}
      </p>
      )}
      <Routes>
        <Route
          path="/"
          element={
            <ListingsPage
              vertical={vertical}
              setVertical={setVertical}
              filters={filters}
              setFilters={setFilters}
              offset={offset}
              setOffset={setOffset}
              sort={sort}
              setSort={setSort}
              order={order}
              setOrder={setOrder}
            />
          }
        />
        <Route path="/listings/:id" element={<ListingDetail />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
