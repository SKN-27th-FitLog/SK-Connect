import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import RootNavigator from "./RootNavigator";
import PostDetailScreen from "../screens/PostDetailScreen";
import PostCreateScreen from "../screens/PostCreateScreen";
import PostListScreen from "../screens/PostListScreen";

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
      }} 
    >
      <Stack.Screen name="MainTabs" component={RootNavigator} />

      <Stack.Screen
        name="PostCreate"
        component={PostCreateScreen}
        options={{ headerShown: false }}
      />

      <Stack.Screen
        name="PostDetail"
        component={PostDetailScreen}
        options={{ headerShown: false }}
      />
    </Stack.Navigator>
  );
}
