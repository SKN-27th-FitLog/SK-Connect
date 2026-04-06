import React from "react";
import { View, StyleSheet } from "react-native";
import { colors, radius } from "../../theme";

export function Card({ children, style, ...props }) {
  return (
    <View style={[styles.card, style]} {...props}>
      {children}
    </View>
  );
}

export function CardHeader({ children, style, ...props }) {
  return <View style={[styles.header, style]} {...props}>{children}</View>;
}

export function CardTitle({ children, style, ...props }) {
  return <View style={[styles.title, style]} {...props}>{children}</View>;
}

export function CardContent({ children, style, ...props }) {
  return <View style={[styles.content, style]} {...props}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.xl,
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  header: {
    padding: 16,
    paddingBottom: 8,
  },
  title: {
    paddingHorizontal: 16,
  },
  content: {
    padding: 16,
  },
});
