import React, { useMemo, useState } from "react";
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
import { updatePost } from "../store/postStore";
import { postDetailStyles as styles } from "../styles/postStyles";

export default function PostDetailScreen({ navigation, route }) {
  const postFromRoute = route?.params?.post;

  const post = useMemo(
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

  const [liked, setLiked] = useState(post.liked ?? false);
  const [likeCount, setLikeCount] = useState(post.likeCount ?? 0);
  const [comments, setComments] = useState(post.comments ?? []);
  const [commentText, setCommentText] = useState("");

  const deleteComment = () => {};

  const saveCommentToServer = () => {};

  const syncPostToServer = () => {};

  const formatDateTime = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const date = now.getDate();
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");

    return `${year}. ${month}. ${date}. ${hours}:${minutes}`;
  };

  const handleLikePress = () => {
    const nextLiked = !liked;
    const nextLikeCount = nextLiked
      ? likeCount + 1
      : Math.max(likeCount - 1, 0);

    setLiked(nextLiked);
    setLikeCount(nextLikeCount);
  };

  const handleCommentSubmit = () => {
    const trimmed = commentText.trim();

    if (!trimmed) {
      Alert.alert("입력 확인", "댓글 내용을 입력해주세요.");
      return;
    }

    const newComment = {
      id: Date.now().toString(),
      author: "익명",
      authorBadge: "익",
      createdAt: formatDateTime(),
      content: trimmed,
    };

    const nextComments = [...comments, newComment];

    setComments(nextComments);
    setCommentText("");
  };

  const handleGoBack = () => {
    const updatedPost = {
      ...post,
      liked,
      likeCount,
      commentCount: comments.length,
      comments,
    };

    updatePost(updatedPost);

    navigation.navigate("MainTabs",{screen:"PostList",params:{updatedPost}});
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
