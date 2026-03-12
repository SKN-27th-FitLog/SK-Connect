import { StyleSheet } from "react-native";
import { ui } from "./ui";

export const styles = StyleSheet.create({
    container: {
        ...ui.whitePage,
        alignItems: "center",
        justifyContent: "center",
        paddingHorizontal: ui.scale(24),
    },

    text: {
        color: ui.colors.gray[600],
        fontSize: ui.scale(16),
        fontWeight: "500",
    },
});