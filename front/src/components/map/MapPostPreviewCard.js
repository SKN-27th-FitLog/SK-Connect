import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';

export default function MapPostPreviewCard({ post, onClose, onPressViewPost }) {
  if (!post || !post.location) return null;

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.category}>📚 {post.category} · 게시글</Text>
        <TouchableOpacity onPress={onClose}>
          <Text style={styles.close}>✕</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.title} numberOfLines={1}>
        {post.title}
      </Text>

      <Text style={styles.content} numberOfLines={2}>
        {post.content}
      </Text>

      <Text style={styles.location}>📍 {post.location}</Text>

      <TouchableOpacity
        style={styles.button}
        onPress={() => onPressViewPost?.(post)}
      >
        <Text style={styles.buttonText}>게시글 보기</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: 250,
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000000',
    shadowOpacity: 0.15,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  category: {
    fontSize: 16,
    fontWeight: '700',
    color: '#F97316',
  },
  close: {
    fontSize: 18,
    color: '#6B7280',
  },
  title: {
    fontSize: 17,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 10,
  },
  content: {
    fontSize: 14,
    lineHeight: 21,
    color: '#334155',
    marginBottom: 12,
  },
  location: {
    fontSize: 14,
    color: '#94A3B8',
    marginBottom: 16,
  },
  button: {
    height: 46,
    borderRadius: 10,
    backgroundColor: '#F97316',
    justifyContent: 'center',
    alignItems: 'center',
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});