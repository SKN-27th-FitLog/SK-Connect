import React from "react";
import { TouchableOpacity, Text } from "react-native";

export default function FloatingButton({ label = "+", onPress }) {
    return (
        <TouchableOpacity
        onPress={onPress}
        style={{
            position: "absolute",
            right: 20,
            bottom: 24,
            width: 56,
            height: 56,
            borderRadius: 28,
            backgroundColor: "#222",
            justifyContent: "center",
            alignItems: "center",
        }}
        >
        <Text style={{ color: "#fff", fontSize: 24, fontWeight: "700" }}>
            {label}
        </Text>
        </TouchableOpacity>
    );
    }