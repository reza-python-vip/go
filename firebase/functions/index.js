const functions = require('firebase-functions');
const admin = require('firebase-admin');

admin.initializeApp();
const db = admin.firestore();

exports.ingestScan = functions.https.onRequest(async (req, res) => {
  try {
    const body = req.body || {};
    if (!Array.isArray(body.nodes)) {
      return res.status(400).send('nodes array required');
    }
    const batch = db.batch();
    const col = db.collection('curated');
    body.nodes.forEach((n) => {
      const id = col.doc().id;
      batch.set(col.doc(id), { node: n, created: admin.firestore.FieldValue.serverTimestamp() });
    });
    await batch.commit();
    return res.status(200).send({ written: body.nodes.length });
  } catch (err) {
    console.error(err);
    return res.status(500).send('internal error');
  }
});

// Sends a notification when a new document is created in the 'curated' collection.
exports.sendNewNodeNotification = functions.firestore
  .document('curated/{docId}')
  .onCreate(async (snap, context) => {
    console.log('New node detected, preparing notification.');

    const notificationBody = 'یک سرور جدید برای شما اضافه شد\nبرای مشاهده کلیک کنید';
    const newNodeData = snap.data();

    // Construct the notification message with platform-specific fields and data payload
    const payload = {
      notification: {
        title: 'سرور جدید V2Ray',
        body: notificationBody
      },
      data: {
        node: newNodeData.node
      },
      android: {
        notification: {
          body: notificationBody,
          click_action: 'FLUTTER_NOTIFICATION_CLICK' // Common action for Flutter apps
        }
      },
      apns: {
        payload: {
          aps: {
            category: 'NEW_NODE_CATEGORY'
          }
        }
      }
    };

    const topic = 'all_users'; // Target topic

    console.log(`Sending notification to topic: ${topic}`);

    try {
      // Send the message to the specified topic
      const response = await admin.messaging().sendToTopic(topic, payload);
      console.log('Successfully sent notification:', response);
    } catch (error) {
      console.error('Error sending notification:', error);
    }
  });
