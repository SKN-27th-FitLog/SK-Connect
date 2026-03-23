import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { View, Text, StyleSheet, Platform } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import PostListScreen from "../screens/PostListScreen";
import CommunityScreen from "../screens/CommunityScreen";
import ChatScreen from "../screens/ChatScreen";
import MyPageScreen from "../screens/MyPageScreen";
import MapScreen from "../screens/MapScreen";
import { colors, spacing } from "../theme";

const Tab = createBottomTabNavigator();

const TAB_ICONS = {
  Home: { active: "home", inactive: "home-outline" },
  Community: { active: "people", inactive: "people-outline" },
  Chat: { active: "chatbubble", inactive: "chatbubble-outline" },
  Map: { active: "map", inactive: "map-outline" },
  MyPage: { active: "person", inactive: "person-outline" },
};

const TAB_LABELS = {
  Home: "홈",
  Community: "커뮤니티",
  Chat: "채팅",
  Map: "지도",
  MyPage: "마이페이지",
};

function TabItem({ name, focused }) {
  const iconName = focused ? TAB_ICONS[name]?.active : TAB_ICONS[name]?.inactive;
  const label = TAB_LABELS[name] || name;
  const color = focused ? colors.primary : colors.gray[400];
  return (
    <View style={styles.tabItem}>
      <View style={styles.iconWrap}>
        <Ionicons name={iconName} size={24} color={color} />
      </View>
      <Text style={[styles.label, { color }]}>{label}</Text>
    </View>
  );
}

export default function RootNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: true,
        tabBarShowLabel: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.gray[400],
        tabBarStyle: styles.tabBar,
        tabBarItemStyle: styles.tabBarItem,
      }}
    >
      <Tab.Screen
        name="Home"
        component={PostListScreen}
        options={{
          title: "홈",
          tabBarIcon: ({ focused }) => (
            <TabItem name="Home" focused={focused} />
          ),
          headerShown: false,
        }}
      />
      <Tab.Screen
        name="Community"
        component={CommunityScreen}
        options={{
          title: "커뮤니티",
          tabBarIcon: ({ focused }) => (
            <TabItem name="Community" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="Chat"
        component={ChatScreen}
        options={{
          title: "채팅",
          tabBarIcon: ({ focused }) => (
            <TabItem name="Chat" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="Map"
        component={MapScreen}
        options={{
          title: "지도",
          tabBarIcon: ({ focused }) => (
            <TabItem name="Map" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="MyPage"
        component={MyPageScreen}
        options={{
          title: "마이페이지",
          tabBarIcon: ({ focused }) => (
            <TabItem name="MyPage" focused={focused} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: colors.white,
    borderTopColor: colors.gray[200],
    borderTopWidth: 1,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: Platform.OS === "ios" ? 49 : spacing.md + 35,
    height: Platform.OS === "ios" ? 113 : 103,
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: -2 },
        shadowOpacity: 0.06,
        shadowRadius: 12,
      },
      default: {
        elevation: 6,
      },
    }),
  },
  tabBarItem: {
    paddingVertical: 6,
    paddingHorizontal: spacing.sm,
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  tabItem: {
    alignItems: "center",
    justifyContent: "center",
  },
  iconWrap: {
    marginBottom: 2,
  },
  label: {
    fontSize: 11,
    fontWeight: "500",
  },
});
