import { Dimensions, Platform } from "react-native";
import { colors, spacing, radius } from "../theme";

const { width, height } = Dimensions.get("window");

const isSmallDevice = width < 360;
const isTablet = width >= 768;

const scale = (size) => {
  if (isTablet) return Math.round(size * 1.12);
  if (isSmallDevice) return Math.round(size * 0.94);
    return size;
};

const verticalScale = (size) => {
  if (height > 900) return Math.round(size * 1.08);
  if (height < 700) return Math.round(size * 0.94);
    return size;
};

const shadow = Platform.select({
    ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.08,
        shadowRadius: 12,
    },
    android: {
        elevation: 4,
    },
    default: {},
});

export const ui = {
    colors,
    spacing,
    radius,
    width,
    height,
    scale,
    verticalScale,
    isSmallDevice,
    isTablet,
    shadow,

    page: {
        flex: 1,
        backgroundColor: colors.gray[50],
    },

    whitePage: {
        flex: 1,
        backgroundColor: colors.white,
    },

    header: {
        backgroundColor: colors.white,
        paddingHorizontal: scale(spacing.lg),
        paddingVertical: verticalScale(spacing.md),
        borderBottomWidth: 1,
        borderBottomColor: colors.gray[100],
    },

    headerTitle: {
        color: colors.primary,
        fontWeight: "700",
        fontSize: scale(18),
    },

    chip: {
        paddingHorizontal: scale(spacing.lg),
        paddingVertical: verticalScale(spacing.sm),
        borderRadius: radius.full,
        backgroundColor: colors.gray[100],
    },

    chipActive: {
        backgroundColor: colors.primary,
    },

    chipText: {
        fontSize: scale(14),
        fontWeight: "500",
        color: colors.gray[600],
    },

    chipTextActive: {
        color: colors.white,
    },

    card: {
        backgroundColor: colors.white,
        borderRadius: scale(radius.xl),
        borderWidth: 1,
        borderColor: colors.gray[100],
        overflow: "hidden",
        ...shadow,
    },

    input: {
        borderWidth: 1,
        borderColor: "#D1D5DB",
        borderRadius: scale(12),
        backgroundColor: colors.white,
        paddingHorizontal: scale(14),
        fontSize: scale(15),
        color: "#111827",
    },

    primaryButton: {
        height: verticalScale(52),
        borderRadius: scale(14),
        backgroundColor: colors.primary,
        justifyContent: "center",
        alignItems: "center",
    },

    primaryButtonText: {
        fontSize: scale(16),
        fontWeight: "700",
        color: colors.white,
    },

    fab: {
        position: "absolute",
        right: scale(spacing.lg),
        bottom: Platform.OS === "ios" ? verticalScale(84) : verticalScale(72),
        width: scale(58),
        height: scale(58),
        borderRadius: scale(29),
        backgroundColor: colors.primary,
        alignItems: "center",
        justifyContent: "center",
        ...shadow,
    },

    fabText: {
        color: colors.white,
        fontSize: scale(26),
        fontWeight: "700",
        lineHeight: scale(28),
    },
};