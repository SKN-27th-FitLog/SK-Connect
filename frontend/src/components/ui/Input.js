import React from "react";
import { TextInput, View, StyleSheet } from "react-native";
import { colors, radius, spacing } from "../../theme";

export function Input({ style, containerStyle, ...props }) {
  return (
    <View style={[styles.container, containerStyle]}>
      <TextInput
        style={[styles.input, style]}
        placeholderTextColor={colors.mutedForeground}
        {...props}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {},
  input: {
    height: 40,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.input,
    paddingHorizontal: spacing.md,
    fontSize: 16,
    color: colors.foreground,
    backgroundColor: "transparent",
  },
});
