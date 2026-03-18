import { getMapMarkers } from "../api/mapApi";

export async function fetchMapMarkers() {
    return await getMapMarkers();
}