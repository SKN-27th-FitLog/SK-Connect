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
          {post.type === "restaurant" 
            ? `${(post.category && (post.category.includes("카페") || post.category.includes("커피"))) ? "☕" : "🍽️"} ${post.category || "맛집"} · 식당` 
            : `📚 ${post.category || "기타"} · 게시글`}
        </Text>
        <TouchableOpacity onPress={onClose}>
          <Text style={mapScreenStyles.postPreviewClose}>✕</Text>
        </TouchableOpacity>
      </View>

      <Text style={mapScreenStyles.postPreviewTitle} numberOfLines={1}>
        {post.title || post.name}
      </Text>

      {post.type === "post" && post.content ? (
        <Text style={mapScreenStyles.postPreviewContent} numberOfLines={2}>
          {post.content}
        </Text>
      ) : null}

      {post.type === "restaurant" && (
        <View style={mapScreenStyles.postPreviewRestaurantInfo}>
          {/* 별점 영역 */}
          <View style={mapScreenStyles.postPreviewSection}>
            <Text style={mapScreenStyles.postPreviewSectionTitle}>별점</Text>
            <Text style={mapScreenStyles.postPreviewSectionContent}>⭐ 별점: 3.0 / 5.0</Text>
          </View>

          {/* 시그니처 메뉴 영역 */}
          {post.signature_menu && post.signature_menu.length > 0 && (
            <View style={mapScreenStyles.postPreviewSection}>
              <Text style={mapScreenStyles.postPreviewSectionTitle}>대표 메뉴</Text>
              <Text style={mapScreenStyles.postPreviewSectionContent}>
                {post.signature_menu.join(", ")}
              </Text>
            </View>
          )}

          {/* 상세 메뉴 안내 영역 */}
          <View style={mapScreenStyles.postPreviewSection}>
            <Text style={mapScreenStyles.postPreviewSectionTitle}>상세 메뉴</Text>
            <Text style={mapScreenStyles.postPreviewSectionContent}>
              상세 메뉴와 가격은 나중에 추가될 예정입니다.
            </Text>
          </View>
        </View>
      )}

      <Text style={mapScreenStyles.postPreviewLocation}>🗺️ {location}</Text>

      {post.type === "post" && (
        <TouchableOpacity
          style={mapScreenStyles.postPreviewButton}
          onPress={() => onPressViewPost?.(post)}
        >
          <Text style={mapScreenStyles.postPreviewButtonText}>게시글 보기</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}
