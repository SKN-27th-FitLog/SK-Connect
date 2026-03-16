import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
} from 'react-native';

export default function PostCard({ post, onPress }) {
  const [liked, setLiked] = useState(post?.liked ?? false);
  const [likeCount, setLikeCount] = useState(post?.likeCount ?? 0);

  if (!post) return null;

  const handleLikePress = () => {
    const nextLiked = !liked;
    setLiked(nextLiked);
    setLikeCount((prev) => (nextLiked ? prev + 1 : Math.max(prev - 1, 0)));
  };

  return (
    <TouchableOpacity
      activeOpacity={0.9}
      style={styles.card}
      onPress={() => onPress?.(post)}
    >
      {post.imageUrl ? (
        <Image source={{ uri: post.imageUrl }} style={styles.image} />
      ) : null}

      <View style={styles.body}>
        <View style={styles.authorRow}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{post.authorBadge || '익'}</Text>
          </View>

          <View>
            <Text style={styles.author}>{post.author}</Text>
            <Text style={styles.date}>{post.createdAt}</Text>
          </View>
        </View>

        <Text style={styles.title} numberOfLines={1}>
          {post.title}
        </Text>

        <Text style={styles.content} numberOfLines={2}>
          {post.content}
        </Text>

        <View style={styles.footer}>
          <TouchableOpacity
            onPress={handleLikePress}
            activeOpacity={0.8}
            style={styles.footerButton}
          >
            <Text style={styles.footerText}>{liked ? '♥' : '♡'} {likeCount}</Text>
          </TouchableOpacity>

          <View style={styles.footerButton}>
            <Text style={styles.footerText}>💬 댓글 {post.commentCount}</Text>
          </View>

          <View style={styles.footerButton}>
            <Text style={styles.footerTextDisabled}>↗ 공유</Text>
          </View>
        </View>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: 16,
    marginTop: 14,
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#ECECEC',
  },
  image: {
    width: '100%',
    height: 240,
    backgroundColor: '#E5E7EB',
  },
  body: {
    padding: 20,
  },
  authorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 18,
  },
  badge: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#F97316',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  badgeText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  author: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  date: {
    marginTop: 4,
    fontSize: 14,
    color: '#94A3B8',
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
    color: '#0F172A',
    marginBottom: 10,
  },
  content: {
    fontSize: 15,
    lineHeight: 24,
    color: '#334155',
    marginBottom: 18,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
    paddingTop: 14,
  },
  footerButton: {
    marginRight: 24,
  },
  footerText: {
    fontSize: 15,
    color: '#6B7280',
  },
  footerTextDisabled: {
    fontSize: 15,
    color: '#C0C7D1',
  },
});