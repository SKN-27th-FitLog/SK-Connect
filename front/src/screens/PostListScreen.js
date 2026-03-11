import React, { useEffect, useState } from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from "react-native";
import { getPosts } from "../api/postApi";
import { colors, spacing, radius } from "../theme";

const TABS = [
  { key: "popular", label: "인기" },
  { key: "interest", label: "내 관심" },
  { key: "category", label: "카테고리" },
  { key: "latest", label: "최신" },
];

function PostCard({ item }) {
  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>익</Text>
        </View>
        <View style={styles.userInfo}>
          <Text style={styles.userName}>익명</Text>
          <Text style={styles.date}>2026. 2. 22.</Text>
        </View>
      </View>
      {item.image_url ? (
        <View style={styles.image} />
      ) : (
        <View style={styles.imagePlaceholder} />
      )}
      <View style={styles.cardContent}>
        <Text style={styles.title} numberOfLines={1}>
          {item.title || "제목"}
        </Text>
        <Text style={styles.content} numberOfLines={2}>
          {item.content || "내용"}
        </Text>
        <View style={styles.actions}>
          <View style={styles.actionItem}>
            <Text style={styles.heart}>♥</Text>
            <Text style={styles.actionText}>{item.like_count ?? 0}</Text>
          </View>
          <Text style={styles.actionText}>댓글</Text>
          <Text style={styles.actionText}>공유</Text>
        </View>
      </View>
    </View>
  );
}

export default function PostListScreen() {
  const [posts, setPosts] = useState([]);
  const [activeTab, setActiveTab] = useState("popular");

  useEffect(() => {
    loadPosts();
  }, []);

  const loadPosts = async () => {
    const data = await getPosts();
    setPosts(data.results || []);
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>SK Connect</Text>
        <View style={styles.tabs}>
          {TABS.map((tab) => (
            <TouchableOpacity
              key={tab.key}
              onPress={() => setActiveTab(tab.key)}
              style={[
                styles.tab,
                activeTab === tab.key && styles.tabActive,
              ]}
            >
              <Text
                style={[
                  styles.tabText,
                  activeTab === tab.key && styles.tabTextActive,
                ]}
              >
                {tab.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
      <View style={styles.list}>
        <FlatList
          data={posts}
          keyExtractor={(item) => item.id?.toString() ?? String(Math.random())}
          renderItem={({ item }) => <PostCard item={item} />}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyText}>게시글이 없습니다</Text>
            </View>
          }
        />
      </View>
      <TouchableOpacity style={styles.fab} activeOpacity={0.8}>
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray[50] },
  header: {
    backgroundColor: colors.white,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.gray[100],
  },
  headerTitle: {
    color: colors.primary,
    fontWeight: "700",
    fontSize: 18,
    marginBottom: spacing.md,
  },
  tabs: { flexDirection: "row", gap: spacing.sm },
  tab: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: radius.full,
    backgroundColor: colors.gray[100],
  },
  tabActive: {
    backgroundColor: colors.primary,
  },
  tabText: {
    fontSize: 14,
    fontWeight: "500",
    color: colors.gray[600],
  },
  tabTextActive: {
    color: colors.white,
  },
  list: { flex: 1, paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: 96 },
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    overflow: "hidden",
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.gray[100],
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { color: colors.white, fontWeight: "600", fontSize: 14 },
  userInfo: { marginLeft: spacing.sm },
  userName: { color: colors.gray[800], fontWeight: "500" },
  date: { color: colors.gray[400], fontSize: 12 },
  image: { width: "100%", height: 192, backgroundColor: colors.gray[100] },
  imagePlaceholder: {
    height: 144,
    backgroundColor: colors.gray[50],
    marginHorizontal: spacing.lg,
    marginBottom: spacing.sm,
    borderRadius: radius.lg,
  },
  cardContent: { padding: spacing.lg, paddingTop: 0 },
  title: {
    fontWeight: "700",
    fontSize: 16,
    color: colors.gray[900],
  },
  content: {
    fontSize: 14,
    color: colors.gray[600],
    marginTop: 4,
  },
  actions: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.lg,
    marginTop: spacing.md,
  },
  actionItem: { flexDirection: "row", alignItems: "center", gap: 4 },
  heart: { color: colors.primary },
  actionText: { fontSize: 14, color: colors.gray[500] },
  empty: { paddingVertical: 64, alignItems: "center" },
  emptyText: { color: colors.gray[400] },
  fab: {
    position: "absolute",
    right: spacing.lg,
    bottom: 112,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  fabText: { color: colors.white, fontSize: 24 },
});
