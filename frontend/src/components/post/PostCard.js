import React from "react";
import { View, Text, TouchableOpacity, Image } from "react-native";

export default function PostCard({ post, onPress }) {
    return (
        <TouchableOpacity onPress={() => onPress(post)}>
        <View style={{ padding: 16, backgroundColor: "#fff", marginBottom: 12, borderRadius: 12 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 8 }}>
            <Text>{post.author || "익명"}</Text>
            <Text>{post.createdAt}</Text>
            </View>

            <Text style={{ fontSize: 16, fontWeight: "700", marginBottom: 6 }}>
            {post.title}
            </Text>

            <Text numberOfLines={2} style={{ marginBottom: 8 }}>
            {post.content}
            </Text>

            {!!post.imageUrl && (
            <Image
                source={{ uri: post.imageUrl }}
                style={{ width: "100%", height: 160, borderRadius: 10, marginBottom: 10 }}
                resizeMode="cover"
            />
            )}

            <View style={{ flexDirection: "row", gap: 12 }}>
            <Text>좋아요 {post.likeCount || 0}</Text>
            <Text>댓글 {post.commentCount || 0}</Text>
            </View>
        </View>
        </TouchableOpacity>
    );
}