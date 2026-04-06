import axios from "axios";

const API_BASE_URL = "http://10.0.2.2:8000";

export const getMapMarkers = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/api/map/markers/`);
        return response.data.markers || [];
    } catch (error) {
        console.error("=== getMapMarkers 에러 ===");
        console.error("message:", error.message);
        console.error("url:", `${API_BASE_URL}/api/map/markers/`);
        console.error("method:", "get");
        console.error("status:", error.response?.status);
        console.error("response:", error.response?.data);
        throw error;
    }
    };

    export const getMapMarkerDetail = async (map_id) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/api/map/markers/${map_id}/`);
        return response.data.markers || [];
    } catch (error) {
        console.error("=== getMapMarkerDetail 에러 ===");
        console.error("message:", error.message);
        console.error("url:", `${API_BASE_URL}/api/map/markers/${map_id}/`);
        console.error("method:", "get");
        console.error("status:", error.response?.status);
        console.error("response:", error.response?.data);
        throw error;
    }
};