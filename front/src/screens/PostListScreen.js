import React, { useEffect, useState } from "react";
import { View, Text, FlatList } from "react-native";
import { getPosts } from "../api/postApi";

export default function PostListScreen() {
    const [posts, setPosts] = useState([]);

    useEffect(() => {
        loadPosts();
    }, []);

    const loadPosts = async () => {
        const data = await getPosts();
        setPosts(data.results);
    };

    return (
        <View>
            <FlatList
                data={posts}
                keyExtractor={(item) => item.id.toString()}
                renderItem={({ item }) => (
                    <View>
                        <Text>{item.title}</Text>
                        <Text>{item.content}</Text>
                    </View>
                )}
            />
        </View>
    );
}