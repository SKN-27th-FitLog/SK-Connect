import React from "react";
import { View, Text, FlatList, TouchableOpacity } from "react-native";
import { postListStyles as styles } from "../styles/postStyles";

import { POST_TABS } from "../constants/PostTabs";
import { CATEGORY_OPTIONS } from "../constants/PostTabs";

import PostCard from "../components/post/PostCard";
import usePosts from "../hooks/usePosts";
import PostTabs from "../components/post/PostTabs";
import CategoryTabs from "../components/post/CategoryTabs";

export default function PostListScreen({ navigation, route }) {
  const {
    filteredPosts,
    activeTab,
    selectedCategory,
    setActiveTab,
    setSelectedCategory,
  } = usePosts(route);

  // [선택 변경] 기존 post 전달 유지 + postId 추가
  const handlePressPost = (post) => {
    navigation.navigate("PostDetail", {
      post,
      postId: post.id, // [추가]
    });
  };

  const handlePressWrite = () => {
    navigation.navigate("PostCreate");
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>SK Connect</Text>

        <View style={styles.tabsRow}>
          <PostTabs
            tabs={POST_TABS}
            activeTab={activeTab}
            onChangeTab={(tabKey) => {
              setActiveTab(tabKey);
              if (tabKey !== "category") {
                setSelectedCategory(null);
              }
            }}
          />
        </View>
      </View>

      {activeTab === "category" && (
        <View style={styles.categoryTabsWrapper}>
          <CategoryTabs
            categories={CATEGORY_OPTIONS}
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
          />
        </View>
      )}

      <View style={styles.list}>
        <FlatList
          data={filteredPosts}
          extraData={filteredPosts}
          keyExtractor={(item, index) => item?.id?.toString() ?? `post-${index}`}
          renderItem={({ item }) => (
            <PostCard post={item} onPress={handlePressPost} />
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
        onPress={handlePressWrite}
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
    </View>
  );
}