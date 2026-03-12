import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
} from "react-native";
//import { getPosts } from "../api/postApi";
import { getPosts } from "../store/postStore";
import { postListStyles as styles } from "../styles/postStyles";
import { ScrollView } from "react-native";

const TABS = [
  { key: "popular", label: "인기" },
  { key: "interest", label: "내 관심" },
  { key: "category", label: "카테고리" },
  { key: "latest", label: "최신" },
];
const CATEGORY_OPTIONS = [
  { key: "study", label: "스터디" },
  { key: "exercise", label: "운동" },
  { key: "restaurant", label: "맛집" },
  { key: "hobby", label: "취미" },
  { key: "networking", label: "네트워킹" },
  { key: "etc", label: "기타" },
];

function PostCard({ item, onPress }) {
  return (
    <TouchableOpacity
      style={styles.card}
      activeOpacity={0.9}
      onPress={onPress}
    >
      <View style={styles.cardHeader}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{item.authorBadge || "익"}</Text>
        </View>
        <View style={styles.userInfo}>
          <Text style={styles.userName}>{item.author || "익명"}</Text>
          <Text style={styles.date}>{item.createdAt || "2026. 2. 22."}</Text>
        </View>
      </View>

      {item.imageUrl || item.image_url ? (
        <View style={styles.image} />
      ) : (
        <View style={styles.imagePlaceholder} />
      )}

      <View style={styles.cardContent}>
        <Text style={styles.title} numberOfLines={1}>
          {item.title || "제목"}
        </Text>
        <Text style={styles.content} numberOfLines={2}>
          {item.content || "내용"}
        </Text>

        <View style={styles.actions}>
          <View style={styles.actionItem}>
            <Text style={styles.heart}>♥</Text>
            <Text style={styles.actionText}>
              {item.likeCount ?? item.like_count ?? 0}
            </Text>
          </View>

          <Text style={styles.actionText}>
            댓글 {item.commentCount ?? item.comments?.length ?? 0}
          </Text>

          <Text style={styles.actionText}>공유</Text>
        </View>
      </View>
    </TouchableOpacity>
  );
}

export default function PostListScreen({ navigation, route }) {
  const [selectedCategory, setSelectedCategory] = useState("study");
  const [posts, setPosts] = useState(getPosts());
  const [activeTab, setActiveTab] = useState("popular");

  
  useEffect(() => {
    const newPost = route?.params?.newPost;

    if (newPost) {
      setPosts([...getPosts()]);
      navigation.setParams({ newPost: undefined });
    }
  }, [route?.params?.newPost]);

  useEffect(() => {
    const updatedPost = route?.params?.updatedPost;

    if (updatedPost) {
      setPosts([...getPosts()]);
      navigation.setParams({ updatedPost: undefined });
    }
  }, [route?.params?.updatedPost]);


  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>SK Connect</Text>

        <View style={styles.tabs}>
          {TABS.map((tab) => (
            <TouchableOpacity
              key={tab.key}
              onPress={() => {
                setActiveTab(tab.key);
                if (tab.key !== "category") {
                  setSelectedCategory("study");
                } 
              }}
              style={[
                styles.tab,
                activeTab === tab.key && styles.tabActive,
              ]}
            >
              <Text
                style={[
                  styles.tabText,
                  activeTab === tab.key && styles.tabTextActive,
                ]}
              >
                {tab.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
      {activeTab === "category" && (
        <View style={styles.categoryTabsWrapper}>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.categoryTabs}
          >
            {CATEGORY_OPTIONS.map((category) => (
              <TouchableOpacity
                key={category.key}
                onPress={() => setSelectedCategory(category.key)}
                style={[
                  styles.tab,
                  selectedCategory === category.key && styles.tabActive,
                ]}
              >
                <Text
                  style={[
                    styles.tabText,
                    selectedCategory === category.key && styles.tabTextActive,
                  ]}
                >
                  {category.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      )}

      <View style={styles.list}>
        <FlatList
          data={posts}
          extraData={posts}
          keyExtractor={(item, index) => item?.id?.toString() ?? `post-${index}`}
          renderItem={({ item }) => (
            <PostCard
              item={item}
              onPress={() => navigation.navigate("PostDetail", { post: item })}
            />
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyText}>게시글이 없습니다</Text>
            </View>
          }
          showsVerticalScrollIndicator={false}
        />
      </View>

      <TouchableOpacity
        style={styles.fab}
        activeOpacity={0.8}
        onPress={() => navigation.navigate("PostCreate")}
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
    </View>
  );
}