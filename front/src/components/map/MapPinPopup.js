/**
 * 지도에서 선택된 핀 단순 정보 팝업 (제목, 설명 위주)
 * - 스타일: front/src/styles/map.js 에서 import
 * - pin.description 또는 pin.content 지원
 */
import React from "react";
import { View, Text, TouchableOpacity } from "react-native";
import mapScreenStyles from "../../styles/map";

export default function MapPinPopup({ pin, onClose, onViewPost }) {
  if (!pin) return null;
  const description = pin.description ?? pin.content;

  return (
    <View style={mapScreenStyles.pinPopupContainer}>
      <Text style={mapScreenStyles.pinPopupTitle}>{pin.title}</Text>
      {description ? (
        <Text style={mapScreenStyles.pinPopupDescription}>{description}</Text>
      ) : null}

      <View style={mapScreenStyles.pinPopupButtonRow}>
        <TouchableOpacity
          onPress={onViewPost}
          style={mapScreenStyles.pinPopupButtonPrimary}
        >
          <Text style={mapScreenStyles.pinPopupButtonText}>게시글 보기</Text>
        </TouchableOpacity>
        <TouchableOpacity
          onPress={onClose}
          style={mapScreenStyles.pinPopupButtonSecondary}
        >
          <Text>닫기</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}
