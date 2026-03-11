import React from "react";
import { View, Text, StyleSheet } from "react-native";

export default function PostDetailScreen({ route }) {
  const { postId } = route?.params ?? {};
  return (
    <View style={styles.container}>
      <Text>게시글 상세 (ID: {postId ?? "-"})</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, justifyContent: "center", alignItems: "center" },
});
