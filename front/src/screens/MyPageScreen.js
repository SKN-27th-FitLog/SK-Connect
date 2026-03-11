import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors } from "../theme";

export default function MyPageScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>마이페이지</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white, alignItems: "center", justifyContent: "center" },
  text: { color: colors.gray[600], fontSize: 16 },
});
