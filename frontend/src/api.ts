const API_URL = import.meta.env.VITE_API_URL;

export type Vertical = "car" | "mc";
export type SortField = "price" | "year" | "mileage" | "make" | "model" | "engine_cc" | "last_seen";
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
    image_urls: string[];
    engine_cc: number | null;
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
    mileage_min?: number;
    mileage_max?: number;
    make?: string[];
    model?: string[];
    search?: string;
    location?: string;
    year_min?: number;
    year_max?: number;
    sort?: SortField;
    order?: SortOrder;
    limit?: number;
    offset?: number;
    [key: string]: unknown;
}

async function request<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    const url = new URL(path, API_URL);
    if(params) {
        for (const [key, value] of Object.entries(params)){
            if (value === undefined || value === null) continue;
            if (Array.isArray(value)) {
                for (const item of value) {
                    url.searchParams.append(key, String(item));
                }
            } else {
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

export function getMakes(vertical: Vertical): Promise<string[]> {
    return request<string[]>("/listings/makes", { vertical });
}

export function getModels(vertical: Vertical, make?: string[]): Promise<string[]> {
    return request<string[]>("/listings/models", { vertical, make });
}