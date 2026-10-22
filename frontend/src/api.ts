const API_URL = import.meta.env.VITE_API_URL;

export type Vertical = "car" | "mc";
export type SortField = "price" | "year" | "mileage" | "last_seen";
export type SortOrder = "asc" | "desc";

export interface Listing{
    id: number;
    vertical: Vertical;
    url: string;
    location: string;
    price_sek: number | null;
    year: number;
    mileage_km: number | null;
    make: string;
    model: string | null;
    model_specification: string | null;
    first_seen: string;
    last_seen: string;
}

export interface ListingPage{
    items: Listing[];
    total: number;
    limit: number;
    offset: number;   
}

export interface ListingsQuery{
    vertical: Vertical,
    price_min?: number;
    price_max?: number;
    make?: string;
    location?: string;
    year?: number;
    sort?: SortField;
    order?: SortOrder;
    limit?: number;
    offset?: number;
}

async function request<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    const url = new URL(path, API_URL);
    if(params) {
        for (const [key, value] of Object.entries(params)){
            if (value !== undefined && value !== null) {
                url.searchParams.set(key, String(value));
            }
        }
    }

    const res = await fetch(url);

    if(!res.ok) {
        throw new Error(`${res.status} ${res.statusText}`);
    }

    return res.json() as Promise<T>;
}

export function getListings(query: ListingsQuery): Promise<ListingPage> {
  return request<ListingPage>("/listings", query);
}

export function getListing(id: number): Promise<Listing> {
    return request<Listing>(`/listings/${id}`);

}