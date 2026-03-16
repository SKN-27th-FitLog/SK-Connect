import React, { useMemo, useState } from 'react';
import {
        SafeAreaView,
        View,
        Text,
        StyleSheet,
        TouchableOpacity,
        FlatList,
        Image,
    } from 'react-native';

    // 게시글 상태 관리
    const [posts, setPosts] = useState(initialPosts);
    
    const handleCreatePost = () => {
    navigation.navigate('CreatePost', {
        onSubmitPost: (newPost) => {
        setPosts((prev) => [newPost, ...prev]);
        },
    });
    }; 

    import PostCard from '../components/common/PostCard';
    // 게시글 상세 페이지로 이동
    const renderPostItem = ({ item }) => (
    <PostCard
        post={item}
        onPress={(post) => navigation?.navigate('PostDetail', { post })}
    />
    );

    export default function Home({ navigation }) {
    const [selectedTab, setSelectedTab] = useState('popular');


    const mockPosts = useMemo(
        () => [
        {
            id: '1',
            author: '익명',
            date: '2026. 2. 22.',
            title: 'SKT 부트캠프 첫 주차 후기',
            content:
            '안녕하세요! SKT 부트캠프 첫 주차가 끝났습니다. 다양한 분들을 만나 네트워킹하고 새로운 기술 스택도 배우는 좋은 경험이었습니다.',
            likes: 6,
            comments: 0,
            image:
            'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=1200&auto=format&fit=crop',
        },
        {
            id: '2',
            author: '익명',
            date: '2026. 2. 21.',
            title: '오늘 점심 맛집 추천해요',
            content:
            '근처에 새로 생긴 치킨집 다녀왔는데 꽤 괜찮았습니다. 점심이나 저녁 모임 잡기에도 좋아 보여요.',
            likes: 4,
            comments: 2,
            image:
            'https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?q=80&w=1200&auto=format&fit=crop',
        },
        ],
        []
    );

    const sortedPosts = useMemo(() => {
        if (selectedTab === 'popular') {
        return [...mockPosts].sort((a, b) => b.likes - a.likes);
        }
        return mockPosts;
    }, [mockPosts, selectedTab]);

    const handleTopTabPress = (tabKey) => {
        setSelectedTab(tabKey);
    };

    const handlePostPress = (post) => {
        console.log('게시글 상세로 이동:', post.id);
        // navigation?.navigate('PostDetail', { postId: post.id });
    };

    const handleCreatePost = () => {
        console.log('게시글 작성 페이지 이동');
        // navigation?.navigate('CreatePost');
    };

    const handleBottomNavPress = (menuKey) => {
        if (menuKey === 'home') {
        console.log('홈 이동');
        return;
        }

        if (menuKey === 'map') {
        console.log('지도 이동');
        // navigation?.navigate('MapView');
        return;
        }

        console.log(`${menuKey} 는 아직 구현 전입니다.`);
    };

    const renderPostItem = ({ item }) => (
        <TouchableOpacity
        activeOpacity={0.9}
        style={styles.card}
        onPress={() => handlePostPress(item)}
        >
        <Image source={{ uri: item.image }} style={styles.cardImage} />

        <View style={styles.cardBody}>
            <View style={styles.authorRow}>
            <View style={styles.authorBadge}>
                <Text style={styles.authorBadgeText}>익</Text>
            </View>

            <View>
                <Text style={styles.authorName}>{item.author}</Text>
                <Text style={styles.postDate}>{item.date}</Text>
            </View>
            </View>

            <Text style={styles.postTitle} numberOfLines={1}>
            {item.title}
            </Text>

            <Text style={styles.postContent} numberOfLines={2}>
            {item.content}
            </Text>

            <View style={styles.cardFooter}>
            <TouchableOpacity style={styles.actionButton} activeOpacity={0.8}>
                <Text style={styles.actionText}>♡ {item.likes}</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionButton} activeOpacity={0.8}>
                <Text style={styles.actionText}>💬 댓글</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionButton} activeOpacity={0.8}>
                <Text style={styles.actionText}>↗ 공유</Text>
            </TouchableOpacity>
            </View>
        </View>
        </TouchableOpacity>
    );

    return (
        <SafeAreaView style={styles.safeArea}>
        <View style={styles.container}>
            <FlatList
            data={sortedPosts}
            keyExtractor={(item) => item.id}
            renderItem={renderPostItem}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.listContent}
            ListHeaderComponent={
                <>
                <View style={styles.logoWrapper}>
                    <Text style={styles.logoText}>SK Bootcamp</Text>
                </View>

                <View style={styles.topTabWrapper}>
                    <TopTabButton
                    label="🔥 인기"
                    isActive={selectedTab === 'popular'}
                    onPress={() => handleTopTabPress('popular')}
                    />
                    <TopTabButton
                    label="💗 내 관심"
                    isActive={selectedTab === 'interest'}
                    onPress={() => handleTopTabPress('interest')}
                    />
                    <TopTabButton
                    label="📌 카테고리"
                    isActive={selectedTab === 'category'}
                    onPress={() => handleTopTabPress('category')}
                    />
                    <TopTabButton
                    label="최신"
                    isActive={selectedTab === 'latest'}
                    onPress={() => handleTopTabPress('latest')}
                    />
                </View>
                </>
            }
            />

            <TouchableOpacity
            style={styles.floatingButton}
            activeOpacity={0.85}
            onPress={handleCreatePost}
            >
            <Text style={styles.floatingButtonText}>＋</Text>
            </TouchableOpacity>

            <View style={styles.bottomNav}>
            <BottomNavButton
                label="홈"
                isActive
                isDisabled={false}
                onPress={() => handleBottomNavPress('home')}
            />
            <BottomNavButton
                label="커뮤니티"
                isActive={false}
                isDisabled
                onPress={() => handleBottomNavPress('community')}
            />
            <BottomNavButton
                label="채팅"
                isActive={false}
                isDisabled
                onPress={() => handleBottomNavPress('chat')}
            />
            <BottomNavButton
                label="지도"
                isActive={false}
                isDisabled={false}
                onPress={() => handleBottomNavPress('map')}
            />
            <BottomNavButton
                label="마이페이지"
                isActive={false}
                isDisabled
                onPress={() => handleBottomNavPress('mypage')}
            />
            </View>
        </View>
        </SafeAreaView>
    );
    }

    function TopTabButton({ label, isActive, onPress }) {
    return (
        <TouchableOpacity
        activeOpacity={0.85}
        onPress={onPress}
        style={[styles.topTabButton, isActive && styles.topTabButtonActive]}
        >
        <Text style={[styles.topTabText, isActive && styles.topTabTextActive]}>
            {label}
        </Text>
        </TouchableOpacity>
    );
    }

    function BottomNavButton({ label, isActive, isDisabled, onPress }) {
    return (
        <TouchableOpacity
        activeOpacity={isDisabled ? 1 : 0.8}
        disabled={isDisabled}
        onPress={onPress}
        style={styles.bottomNavButton}
        >
        <Text
            style={[
            styles.bottomNavText,
            isActive && styles.bottomNavTextActive,
            isDisabled && styles.bottomNavTextDisabled,
            ]}
        >
            {label}
        </Text>
        </TouchableOpacity>
    );
    }

    const styles = StyleSheet.create({
    safeArea: {
        flex: 1,
        backgroundColor: '#F7F7F8',
    },
    container: {
        flex: 1,
        backgroundColor: '#F7F7F8',
    },
    listContent: {
        paddingBottom: 120,
    },

    logoWrapper: {
        paddingTop: 8,
        paddingBottom: 14,
        alignItems: 'center',
        backgroundColor: '#FFFFFF',
        borderBottomWidth: 1,
        borderBottomColor: '#EFEFEF',
    },
    logoText: {
        fontSize: 20,
        fontWeight: '800',
        color: '#F97316',
    },

    topTabWrapper: {
        flexDirection: 'row',
        paddingHorizontal: 16,
        paddingVertical: 14,
        backgroundColor: '#FFFFFF',
        gap: 10,
    },
    topTabButton: {
        paddingHorizontal: 18,
        paddingVertical: 12,
        borderRadius: 999,
        backgroundColor: '#F1F2F4',
    },
    topTabButtonActive: {
        backgroundColor: '#F68B2C',
    },
    topTabText: {
        fontSize: 16,
        fontWeight: '500',
        color: '#9CA3AF',
    },
    topTabTextActive: {
        color: '#FFFFFF',
        fontWeight: '700',
    },

    card: {
        marginTop: 14,
        marginHorizontal: 16,
        borderRadius: 22,
        backgroundColor: '#FFFFFF',
        overflow: 'hidden',
        borderWidth: 1,
        borderColor: '#ECECEC',
    },
    cardImage: {
        width: '100%',
        height: 240,
        backgroundColor: '#E5E7EB',
    },
    cardBody: {
        padding: 20,
    },

    authorRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 18,
    },
    authorBadge: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: '#F68B2C',
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 12,
    },
    authorBadgeText: {
        color: '#FFFFFF',
        fontSize: 18,
        fontWeight: '700',
    },
    authorName: {
        fontSize: 16,
        fontWeight: '600',
        color: '#111827',
    },
    postDate: {
        marginTop: 4,
        fontSize: 14,
        color: '#94A3B8',
    },

    postTitle: {
        fontSize: 18,
        fontWeight: '800',
        color: '#0F172A',
        marginBottom: 10,
    },
    postContent: {
        fontSize: 15,
        lineHeight: 24,
        color: '#334155',
        marginBottom: 18,
    },

    cardFooter: {
        flexDirection: 'row',
        alignItems: 'center',
        borderTopWidth: 1,
        borderTopColor: '#F1F5F9',
        paddingTop: 14,
        gap: 24,
    },
    actionButton: {
        justifyContent: 'center',
        alignItems: 'center',
    },
    actionText: {
        fontSize: 15,
        color: '#6B7280',
    },

    floatingButton: {
        position: 'absolute',
        right: 18,
        bottom: 84,
        width: 58,
        height: 58,
        borderRadius: 29,
        backgroundColor: '#F68B2C',
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#000000',
        shadowOpacity: 0.18,
        shadowRadius: 8,
        shadowOffset: { width: 0, height: 4 },
        elevation: 6,
    },
    floatingButtonText: {
        fontSize: 30,
        lineHeight: 32,
        color: '#FFFFFF',
        fontWeight: '700',
    },

    bottomNav: {
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 0,
        height: 68,
        backgroundColor: '#FFFFFF',
        borderTopWidth: 1,
        borderTopColor: '#EAEAEA',
        flexDirection: 'row',
    },
    bottomNavButton: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    bottomNavText: {
        fontSize: 13,
        fontWeight: '500',
        color: '#94A3B8',
    },
    bottomNavTextActive: {
        color: '#F68B2C',
        fontWeight: '800',
    },
    bottomNavTextDisabled: {
        color: '#CBD5E1',
    },
    });