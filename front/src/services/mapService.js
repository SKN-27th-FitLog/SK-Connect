import { getMapMarkers } from "../api/remapApi";

export async function fetchMapMarkers() {
    return await getMapMarkers();
}