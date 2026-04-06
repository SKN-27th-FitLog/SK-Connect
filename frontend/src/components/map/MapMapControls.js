/**
 * 지도 우측: 확대·축소·내 위치 이동
 * - 스타일: styles/map.js
 */
import React from "react";
import { View, TouchableOpacity } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import mapScreenStyles from "../../styles/map";
import { colors } from "../../theme";

export default function MapMapControls({
  onZoomIn,
  onZoomOut,
  onMyLocation,
  locationLoading = false,
}) {
  return (
    <View style={mapScreenStyles.mapControlsColumn}>
      <TouchableOpacity
        style={mapScreenStyles.mapControlButton}
        onPress={onZoomIn}
        accessibilityLabel="지도 확대"
      >
        <Ionicons name="add" size={26} color={colors.primary} />
      </TouchableOpacity>
      <TouchableOpacity
        style={mapScreenStyles.mapControlButton}
        onPress={onZoomOut}
        accessibilityLabel="지도 축소"
      >
        <Ionicons name="remove" size={26} color={colors.primary} />
      </TouchableOpacity>
      <TouchableOpacity
        style={[
          mapScreenStyles.mapControlButton,
          locationLoading && mapScreenStyles.mapControlButtonDisabled,
        ]}
        onPress={onMyLocation}
        disabled={locationLoading}
        accessibilityLabel="내 위치로 이동"
      >
        <Ionicons name="navigate" size={22} color={colors.primary} />
      </TouchableOpacity>
    </View>
  );
}
