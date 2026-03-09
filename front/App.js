import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View } from 'react-native';
import PostListScreen from "./src/screens/PostListScreen";


export default function App() {
  return (
    <View style={styles.container}>
      {/* <Text>!!hello world!</Text> */}
      {/* <StatusBar style="auto" /> */}
      <PostListScreen />
    </View>
    
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
});

