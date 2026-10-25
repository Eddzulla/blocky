import { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import type { SortField, SortOrder, Vertical } from "./api";
import ListingsPage, { defaultFilters } from "./ListingsPage";
import ListingDetail from "./ListingDetail";

function App() {
  const [vertical, setVertical] = useState<Vertical>("car");
  const [filters, setFilters] = useState(defaultFilters("car"));
  const [offset, setOffset] = useState(0);
  const [sort, setSort] = useState<SortField>("last_seen");
  const [order, setOrder] = useState<SortOrder>("desc");

  return (
    <BrowserRouter>
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
