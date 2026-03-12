import React, { useEffect, useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { colors, radius, spacing } from "../theme";
import { DEFAULT_LOCATION } from "../config/map";
import { getMapMarkers } from "../api/mapApi";

function MapPlaceholder() {
  return (
    <View style={styles.mapArea}>
      <Text style={styles.mapPlaceholderText}>
        [지도]{"\n"}웹에서만 지원됩니다.
      </Text>
    </View>
  );
} 

export default function MapScreen() {
  const navigation = useNavigation();
  const [pins, setPins] = useState([]);
  const [selectedPin, setSelectedPin] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const { lat, lng } = DEFAULT_LOCATION;
    const markers = await getMapMarkers({ lat, lng });
    setPins(markers);
  };

  const handlePinPress = (pin) => {
    setSelectedPin(pin);
  };

  const handleViewPost = () => {
    if (!selectedPin) return;
    navigation.navigate("PostDetail", { postId: selectedPin.postId });
    setSelectedPin(null);
  };

  return (
    <View style={styles.container}>
      <MapPlaceholder />

      {selectedPin && (
        <View style={styles.popupOverlay}>
          <View style={styles.popup}>
            <View style={styles.popupHeader}>
              <Text style={styles.popupCategory}>
                {selectedPin.category} · 게시글
              </Text>
              <TouchableOpacity onPress={() => setSelectedPin(null)}>
                <Text style={styles.popupClose}>✕</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.popupTitle}>{selectedPin.title}</Text>
            <Text style={styles.popupContent}>{selectedPin.content}</Text>
            <Text style={styles.popupLocation}>
              📍 {selectedPin.location_name}
            </Text>
            <TouchableOpacity
              style={styles.popupButton}
              onPress={handleViewPost}
              activeOpacity={0.8}
            >
              <Text style={styles.popupButtonText}>게시글 보기</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray[200] },
  mapArea: {
    flex: 1,
    backgroundColor: colors.gray[300],
    alignItems: "center",
    justifyContent: "center",
  },
  mapPlaceholderText: {
    color: colors.gray[500],
    textAlign: "center",
    fontSize: 14,
  },
  popupOverlay: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: "rgba(0,0,0,0.3)",
    padding: spacing.lg,
    alignItems: "center",
  },
  popup: {
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.lg,
    width: "100%",
    maxWidth: 320,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 12,
    elevation: 10,
  },
  popupHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  popupClose: { color: colors.gray[400], fontSize: 18 },
  popupTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: colors.foreground,
  },
  popupContent: { color: colors.gray[600], fontSize: 14, marginTop: 4 },
  popupLocation: {
    color: colors.gray[500],
    fontSize: 14,
    marginTop: spacing.sm,
    marginBottom: spacing.md,
  },
  popupButton: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.sm,
    borderRadius: radius.lg,
    alignItems: "center",
  },
  popupButtonText: { color: colors.white, fontWeight: "500" },
});
