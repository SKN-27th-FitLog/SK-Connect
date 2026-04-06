import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, spacing, radius } from "../theme";

export default function PostCard({ post }) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{post?.title}</Text>
      <Text style={styles.content} numberOfLines={2}>
        {post?.content}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: spacing.lg,
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  title: { fontSize: 16, fontWeight: "600", color: colors.foreground },
  content: { fontSize: 14, color: colors.gray[600], marginTop: 4 },
});
