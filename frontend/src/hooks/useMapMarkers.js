import { useEffect, useState } from "react";
import { getMapMarkers } from "./api/remapApi";

export default function useMapMarkers() {
    const [pins, setPins] = useState([]);
    const [selectedPin, setSelectedPin] = useState(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
        const data = await getMapMarkers();
        setPins(data || []);
        } catch (error) {
        console.error(error);
        }
    };

    const handlePinPress = (pin) => {
        setSelectedPin(pin);
    };

    const clearSelectedPin = () => {
        setSelectedPin(null);
    };

    return {
        pins,
        selectedPin,
        handlePinPress,
        clearSelectedPin,
    };
    }