import React, { useMemo } from "react";
import {
  SafeAreaView,
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  Image,
  TextInput,
  Alert,
} from "react-native";
import CommentItem from "../components/comment/CommentItem";
import { updatePost } from "../store/postStore"; // [주석] 지금 구조 유지용
import { postDetailStyles as styles } from "../styles/postStyles";
import usePostDetail from "../hooks/usePostDetail";

export default function PostDetailScreen({ navigation, route }) {
  const postFromRoute = route?.params?.post;

  const initialPost = useMemo(
    () =>
      postFromRoute || {
        id: "1",
        author: "익명",
        authorBadge: "익",
        createdAt: "2026. 2. 22.",
        title: "기본 게시글",
        content: "기본 게시글 내용입니다.",
        imageUrl: "",
        likeCount: 0,
        liked: false,
        category: "",
        location: "",
        comments: [],
      },
    [postFromRoute]
  );

  const {
    post,
    liked,
    likeCount,
    comments,
    commentText,
    setCommentText,
    handleLikePress,
    handleSubmitComment,
    updatedPost,
  } = usePostDetail(initialPost);

  const handleCommentSubmit = () => {
    if (!commentText.trim()) {
      Alert.alert("입력 확인", "댓글 내용을 입력해주세요.");
      return;
    }

    handleSubmitComment();
  };

  const handleGoBack = () => {
    updatePost(updatedPost); // [주석] 현재 로컬 store 구조 유지
    navigation.navigate("MainTabs", {
      screen: "PostList",
      params: { updatedPost },
    });
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.contentContainer}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <TouchableOpacity onPress={handleGoBack}>
            <Text style={styles.backButton}>‹</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>게시글</Text>
        </View>

        {post.imageUrl ? (
          <Image source={{ uri: post.imageUrl }} style={styles.image} />
        ) : null}

        <View style={styles.section}>
          <View style={styles.authorRow}>
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{post.authorBadge || "익"}</Text>
            </View>
            <View>
              <Text style={styles.author}>{post.author || "익명"}</Text>
              <Text style={styles.date}>{post.createdAt || "2026. 2. 22."}</Text>
            </View>
          </View>

          <Text style={styles.title}>{post.title || "제목 없음"}</Text>
          <Text style={styles.content}>{post.content || "내용이 없습니다."}</Text>

          {post.location ? (
            <View style={styles.locationBox}>
              <Text style={styles.locationLabel}>위치</Text>
              <Text style={styles.locationText}>{post.location}</Text>
            </View>
          ) : null}

          <View style={styles.likeRow}>
            <TouchableOpacity onPress={handleLikePress}>
              <Text style={styles.likeText}>
                {liked ? "♥" : "♡"} {likeCount}
              </Text>
            </TouchableOpacity>
          </View>

          <View style={styles.commentHeader}>
            <Text style={styles.commentTitle}>댓글 {comments.length}</Text>
          </View>

          <View style={styles.commentInputWrapper}>
            <TextInput
              value={commentText}
              onChangeText={setCommentText}
              placeholder="댓글을 입력하세요"
              placeholderTextColor="#9CA3AF"
              style={styles.commentInput}
              multiline
            />
            <TouchableOpacity
              style={styles.commentButton}
              activeOpacity={0.85}
              onPress={handleCommentSubmit}
            >
              <Text style={styles.commentButtonText}>등록</Text>
            </TouchableOpacity>
          </View>

          <View>
            {comments.length > 0 ? (
              comments.map((comment) => (
                <CommentItem key={comment.id} comment={comment} />
              ))
            ) : (
              <Text style={styles.emptyCommentText}>아직 댓글이 없습니다.</Text>
            )}
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}