import React from "react";
import { View, Text, TouchableOpacity } from "react-native";

export default function MapPinPopup({ pin, onClose, onViewPost }) {
    if (!pin) return null;

    return (
        <View
        style={{
            position: "absolute",
            left: 16,
            right: 16,
            bottom: 20,
            backgroundColor: "#fff",
            borderRadius: 16,
            padding: 16,
        }}
        >
        <Text style={{ fontSize: 16, fontWeight: "700", marginBottom: 6 }}>
            {pin.title}
        </Text>
        <Text style={{ marginBottom: 12 }}>{pin.description}</Text>

        <View style={{ flexDirection: "row", gap: 8 }}>
            <TouchableOpacity
            onPress={onViewPost}
            style={{ backgroundColor: "#222", paddingVertical: 10, paddingHorizontal: 14, borderRadius: 10 }}
            >
            <Text style={{ color: "#fff" }}>게시글 보기</Text>
            </TouchableOpacity>

            <TouchableOpacity
            onPress={onClose}
            style={{ backgroundColor: "#eee", paddingVertical: 10, paddingHorizontal: 14, borderRadius: 10 }}
            >
            <Text>닫기</Text>
            </TouchableOpacity>
        </View>
        </View>
    );
    }