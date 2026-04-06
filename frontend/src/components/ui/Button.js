import React from "react";
import { TouchableOpacity, Text, StyleSheet } from "react-native";
import { colors, radius, fontSize, spacing } from "../../theme";

const variants = {
  default: {
    button: { backgroundColor: colors.primary },
    text: { color: colors.white },
  },
  outline: {
    button: { backgroundColor: "transparent", borderWidth: 1, borderColor: colors.border },
    text: { color: colors.foreground },
  },
  secondary: {
    button: { backgroundColor: colors.muted },
    text: { color: colors.foreground },
  },
  ghost: {
    button: { backgroundColor: "transparent" },
    text: { color: colors.foreground },
  },
};

const sizes = {
  default: { paddingVertical: spacing.sm, paddingHorizontal: spacing.lg },
  sm: { paddingVertical: 6, paddingHorizontal: spacing.md },
  lg: { paddingVertical: spacing.md, paddingHorizontal: spacing["2xl"] },
};

export function Button({
  children,
  variant = "default",
  size = "default",
  style,
  textStyle,
  disabled,
  ...props
}) {
  const v = variants[variant] || variants.default;
  const s = sizes[size] || sizes.default;

  return (
    <TouchableOpacity
      style={[
        styles.base,
        v.button,
        s,
        disabled && styles.disabled,
        style,
      ]}
      disabled={disabled}
      activeOpacity={0.8}
      {...props}
    >
      <Text style={[styles.text, v.text, textStyle]}>{children}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  text: {
    fontSize: fontSize.sm,
    fontWeight: "600",
  },
  disabled: {
    opacity: 0.5,
  },
});
