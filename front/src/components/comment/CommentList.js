import React from "react";
import { View, Text } from "react-native";

export default function CommentList({ comments }) {
    return (
        <View style={{ marginTop: 16 }}>
        {comments.map((comment) => (
            <View
            key={comment.id}
            style={{ paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#eee" }}
            >
            <Text style={{ fontWeight: "700", marginBottom: 4 }}>{comment.author}</Text>
            <Text>{comment.content}</Text>
            </View>
        ))}
        </View>
    );
}