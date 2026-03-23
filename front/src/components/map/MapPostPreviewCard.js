/**
 * 지도에서 선택된 핀(게시글) 미리보기 카드
 * - 스타일: front/src/styles/map.js 에서 import
 * - post.location 또는 post.location_name 지원 (pin 구조 호환)
 */
import React from "react";
import { View, Text, TouchableOpacity } from "react-native";
import mapScreenStyles from "../../styles/map";

export default function MapPostPreviewCard({ post, onClose, onPressViewPost }) {
  const location = post?.location ?? post?.location_name;
  if (!post || !location) return null;

  return (
    <View style={mapScreenStyles.postPreviewCard}>
      <View style={mapScreenStyles.postPreviewDragHandle} />
      <View style={mapScreenStyles.postPreviewHeaderRow}>
        <Text style={mapScreenStyles.postPreviewCategory}>
          📚 {post.category} · 게시글
        </Text>
        <TouchableOpacity onPress={onClose}>
          <Text style={mapScreenStyles.postPreviewClose}>✕</Text>
        </TouchableOpacity>
      </View>

      <Text style={mapScreenStyles.postPreviewTitle} numberOfLines={1}>
        {post.title}
      </Text>

      <Text style={mapScreenStyles.postPreviewContent} numberOfLines={2}>
        {post.content}
      </Text>

      <Text style={mapScreenStyles.postPreviewLocation}>📍 {location}</Text>

      <TouchableOpacity
        style={mapScreenStyles.postPreviewButton}
        onPress={() => onPressViewPost?.(post)}
      >
        <Text style={mapScreenStyles.postPreviewButtonText}>게시글 보기</Text>
      </TouchableOpacity>
    </View>
  );
}
