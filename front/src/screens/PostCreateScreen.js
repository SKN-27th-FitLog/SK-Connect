import React from "react";
import { View, Text, StyleSheet } from "react-native";

export default function PostCreateScreen() {
  return (
    <View style={styles.container}>
      <Text>게시글 작성</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, justifyContent: "center", alignItems: "center" },
});
