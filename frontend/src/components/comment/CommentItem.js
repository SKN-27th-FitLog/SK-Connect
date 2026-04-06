import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function CommentItem({ comment }) {
  if (!comment) return null;

  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{comment.authorBadge || '익'}</Text>
        </View>

        <View style={styles.contentArea}>
          <View style={styles.header}>
            <Text style={styles.author}>{comment.author}</Text>
            <Text style={styles.date}>{comment.createdAt}</Text>
          </View>

          <Text style={styles.content}>{comment.content}</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  badge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#E5E7EB',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  badgeText: {
    color: '#6B7280',
    fontSize: 16,
    fontWeight: '600',
  },
  contentArea: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  author: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginRight: 8,
  },
  date: {
    fontSize: 14,
    color: '#94A3B8',
  },
  content: {
    fontSize: 15,
    lineHeight: 22,
    color: '#334155',
  },
});