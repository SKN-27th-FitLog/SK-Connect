import React from "react";
import { View, TextInput, TouchableOpacity, Text } from "react-native";

export default function CommentInput({ value, onChangeText, onSubmit }) {
    return (
        <View style={{ flexDirection: "row", gap: 8, marginTop: 16 }}>
        <TextInput
            value={value}
            onChangeText={onChangeText}
            placeholder="댓글을 입력하세요"
            style={{
            flex: 1,
            borderWidth: 1,
            borderColor: "#ddd",
            borderRadius: 10,
            paddingHorizontal: 12,
            paddingVertical: 10,
            }}
        />
        <TouchableOpacity
            onPress={onSubmit}
            style={{
            backgroundColor: "#222",
            borderRadius: 10,
            justifyContent: "center",
            paddingHorizontal: 14,
            }}
        >
            <Text style={{ color: "#fff" }}>등록</Text>
        </TouchableOpacity>
        </View>
    );
    }