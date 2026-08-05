# MCAP Inspection Report

Generated: 2026-08-05T21:13:18.885089+00:00

This report is produced by `scripts/inspect_mcap.py`, a read-only inspection utility. The source file `data/input/sanitized.mcap` (5,751,237 bytes) was never modified. All relationship-cardinality figures are **estimates for later validation**, not declared primary/foreign keys.

## Topic check

- Expected topics: cv_detections, cv_tracks, radar_detections, track_states
- Found topics: cv_detections, cv_tracks, radar_detections, track_states
- Missing topics: none
- Unexpected topics: none
- All expected topics present: **True**

## Channels

### `cv_tracks` (channel 1, schema `anduril.sensors.cv.v1.CVTrackFrame`)

- Message encoding / schema encoding: `protobuf` / `protobuf`
- Message count: 35,613
- log_time range (ns): 1761244500011495000 .. 1761245699980848000
- publish_time range (ns): 1761244500011495000 .. 1761245699980848000
- Out-of-order log_time messages: 0
- Sequence behavior: monotonic_increasing=False, increasing_steps=0, equal_steps=35612, decreasing_steps=0, duplicate_sequence_values=1, range=[0, 0]
- Field count (recursive): 172
- Structural samples decoded: 3 (indices [0, 17806, 35612])

**Message structure:** `batch_of_entities`

Top-level repeated field 'tracks' shares its name with the topic 'cv_tracks', so each message appears to be a batch/frame containing multiple entities of that type. Companion repeated field(s) also present: ['trackers', 'assets'].

**Candidate identifier field statistics (full dataset):**

| field_path | category | populated | null_freq% | distinct | uniqueness_ratio | dup_within_msg (unexpected) | dup_cross_msg (expected) | entities/msg (min/avg/max) |
|---|---|---|---|---|---|---|---|---|
| `assets.asset_id` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `assets.suppressed_detection_ids` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `metadata.sensor_id` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.0/1 |
| `trackers.tracker_id` | identifier | 35613 | 0.0 | 1 | 0.0 | 0 | 1 | 1/1.0/1 |
| `tracks.last_associated_detection_id` | identifier | 9496 | 0.0 | 1868 | 0.1967 | 0 | 1865 | 0/0.267/2 |
| `tracks.track_id` | identifier | 9496 | 0.0 | 17 | 0.0018 | 0 | 17 | 0/0.267/2 |
| `tracks.update_uid` | identifier | 9496 | 0.0 | 9496 | 1.0 | 0 | 0 | 0/0.267/2 |

<details><summary>Full recursive field catalog</summary>

| path | kind | type | repeated | presence | observed (null/empty/populated) | sample |
|---|---|---|---|---|---|---|
| `capture_time` | message | google.protobuf.Timestamp | False | True | 0/0/3 | <message Timestamp>; <message Timestamp>; <message Timestamp> |
| `capture_time.seconds` | scalar | int64 | False | False | 0/0/3 | 1761244500; 1761245099; 1761245699 |
| `capture_time.nanos` | scalar | int32 | False | False | 0/0/3 | 11495000; 145853000; 980848000 |
| `completion_time` | message | google.protobuf.Timestamp | False | True | 0/0/3 | <message Timestamp>; <message Timestamp>; <message Timestamp> |
| `completion_time.seconds` | scalar | int64 | False | False | 0/0/3 | 1761244500; 1761245099; 1761245700 |
| `completion_time.nanos` | scalar | int32 | False | False | 0/0/3 | 45350000; 216036000; 20326000 |
| `elapsed_duration` | message | google.protobuf.Duration | False | True | 0/0/3 | <message Duration>; <message Duration>; <message Duration> |
| `elapsed_duration.seconds` | scalar | int64 | False | False | 0/3/0 | 0; 0; 0 |
| `elapsed_duration.nanos` | scalar | int32 | False | False | 0/0/3 | 31000; 28000; 11000 |
| `detection_time` | message | google.protobuf.Timestamp | False | True | 3/0/0 | <message Timestamp>; <message Timestamp>; <message Timestamp> |
| `detection_time.seconds` | scalar | int64 | False | False | 0/0/0 |  |
| `detection_time.nanos` | scalar | int32 | False | False | 0/0/0 |  |
| `metadata` | message | anduril.sensors.cv.v1.ImageFrameMetadata | False | True | 0/0/3 | <message ImageFrameMetadata>; <message ImageFrameMetadata>; <message ImageFrameMetadata> |
| `metadata.sensor_id` | scalar | string | False | False | 0/3/0 | ; ;  |
| `metadata.image_width` | scalar | uint32 | False | False | 0/0/3 | 1280; 1280; 1280 |
| `metadata.image_height` | scalar | uint32 | False | False | 0/0/3 | 1024; 1024; 1024 |
| `metadata.horizontal_fov_deg` | scalar | float | False | False | 0/0/3 | 0.8148589134216309; 0.8148589134216309; 0.8148589134216309 |
| `metadata.vertical_fov_deg` | scalar | float | False | False | 0/0/3 | 0.6518911123275757; 0.6518911123275757; 0.6518911123275757 |
| `metadata.focal_length` | scalar | float | False | False | 0/3/0 | 0.0; 0.0; 0.0 |
| `metadata.focus` | scalar | float | False | False | 0/0/3 | 33071.0; 32708.0; 33091.0 |
| `metadata.spectrum` | enum | anduril.sensors.cv.v1.ImageSpectrum | False | False | 0/0/3 | 3; 3; 3 |
| `metadata.pinhole` | message | anduril.sensors.cv.v1.CameraIntrinsicsPinhole | False | True | 3/0/0 | <message CameraIntrinsicsPinhole>; <message CameraIntrinsicsPinhole>; <message CameraIntrinsicsPinhole> |
| `metadata.pinhole.fx` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pinhole.fy` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pinhole.cx` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pinhole.cy` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pinhole.s` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general` | message | anduril.sensors.cv.v1.CameraIntrinsicsGeneral | False | True | 3/0/0 | <message CameraIntrinsicsGeneral>; <message CameraIntrinsicsGeneral>; <message CameraIntrinsicsGeneral> |
| `metadata.general.r1` | message | anduril.type.Vec3 | False | True | 0/0/0 |  |
| `metadata.general.r1.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r1.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r1.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r2` | message | anduril.type.Vec3 | False | True | 0/0/0 |  |
| `metadata.general.r2.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r2.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r2.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r3` | message | anduril.type.Vec3 | False | True | 0/0/0 |  |
| `metadata.general.r3.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r3.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r3.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pose` | message | anduril.type.Pose | False | True | 3/0/0 | <message Pose>; <message Pose>; <message Pose> |
| `metadata.pose.pos` | message | anduril.type.LLA | False | True | 0/0/0 |  |
| `metadata.pose.pos.lon` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pose.pos.lat` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pose.pos.alt` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pose.pos.is2d` | scalar | bool | False | False | 0/0/0 |  |
| `metadata.pose.pos.altitude_reference` | enum | anduril.type.LLA.AltitudeReference | False | False | 0/0/0 |  |
| `metadata.pose.att_enu` | message | anduril.type.Quaternion | False | True | 0/0/0 |  |
| `metadata.pose.att_enu.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pose.att_enu.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pose.att_enu.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pose.att_enu.w` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_pose` | message | anduril.type.Pose | False | True | 3/0/0 | <message Pose>; <message Pose>; <message Pose> |
| `metadata.camera_pose.pos` | message | anduril.type.LLA | False | True | 0/0/0 |  |
| `metadata.camera_pose.pos.lon` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_pose.pos.lat` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_pose.pos.alt` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_pose.pos.is2d` | scalar | bool | False | False | 0/0/0 |  |
| `metadata.camera_pose.pos.altitude_reference` | enum | anduril.type.LLA.AltitudeReference | False | False | 0/0/0 |  |
| `metadata.camera_pose.att_enu` | message | anduril.type.Quaternion | False | True | 0/0/0 |  |
| `metadata.camera_pose.att_enu.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_pose.att_enu.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_pose.att_enu.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_pose.att_enu.w` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_orientation_to_mount` | message | anduril.type.Quaternion | False | True | 3/0/0 | <message Quaternion>; <message Quaternion>; <message Quaternion> |
| `metadata.camera_orientation_to_mount.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_orientation_to_mount.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_orientation_to_mount.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_orientation_to_mount.w` | scalar | double | False | False | 0/0/0 |  |
| `metadata.frame_number` | scalar | uint64 | False | False | 0/0/3 | 3052844; 3070818; 3088843 |
| `metadata.sensor_index` | scalar | uint32 | False | False | 0/0/3 | 2; 2; 2 |
| `metadata.mount_name` | message | google.protobuf.StringValue | False | True | 0/0/3 | <message StringValue>; <message StringValue>; <message StringValue> |
| `metadata.mount_name.value` | scalar | string | False | False | 0/0/3 | PTU; PTU; PTU |
| `metadata.camera_name` | message | google.protobuf.StringValue | False | True | 0/0/3 | <message StringValue>; <message StringValue>; <message StringValue> |
| `metadata.camera_name.value` | scalar | string | False | False | 0/0/3 | MWIR; MWIR; MWIR |
| `trackers` | message | anduril.sensors.cv.v1.CVTrackerMetadata | True | False | 0/0/3 | <message CVTrackerMetadata>; <message CVTrackerMetadata>; <message CVTrackerMetadata> |
| `trackers.tracker_id` | scalar | string | False | False | 0/0/3 | KALMAN_FLOW; KALMAN_FLOW; KALMAN_FLOW |
| `tracks` | message | anduril.sensors.cv.v1.CVTrack | True | False | 0/0/2 | <message CVTrack>; <message CVTrack> |
| `tracks.track_id` | scalar | uint64 | False | False | 0/0/2 | 81754; 82990 |
| `tracks.track_age` | scalar | uint64 | False | False | 0/0/2 | 133; 26 |
| `tracks.status` | enum | anduril.sensors.cv.v1.CVTrackStatus | False | False | 0/0/2 | 3; 3 |
| `tracks.object_class` | enum | anduril.sensors.cv.v1.ObjectClassification | False | False | 0/0/2 | 21; 11 |
| `tracks.class_name` | scalar | string | False | False | 0/0/2 | AIR_VEHICLE; BIRD |
| `tracks.bounding_box` | message | anduril.sensors.cv.v1.BoundingBox | False | True | 0/0/2 | <message BoundingBox>; <message BoundingBox> |
| `tracks.bounding_box.left` | scalar | float | False | False | 0/0/2 | 0.5021061897277832; 0.5282396078109741 |
| `tracks.bounding_box.top` | scalar | float | False | False | 0/0/2 | 0.4821931719779968; 0.532387375831604 |
| `tracks.bounding_box.right` | scalar | float | False | False | 0/0/2 | 0.5697526931762695; 0.5446791648864746 |
| `tracks.bounding_box.bottom` | scalar | float | False | False | 0/0/2 | 0.5270045399665833; 0.5501776933670044 |
| `tracks.last_associated_detection_id` | scalar | uint64 | False | False | 0/0/2 | 81780; 82993 |
| `tracks.score` | scalar | float | False | False | 0/0/2 | 0.92822265625; 0.447998046875 |
| `tracks.focus_score` | message | google.protobuf.FloatValue | False | True | 0/0/2 | <message FloatValue>; <message FloatValue> |
| `tracks.focus_score.value` | scalar | float | False | False | 0/0/2 | 0.06153672933578491; 0.7669925093650818 |
| `tracks.sharpness` | message | google.protobuf.FloatValue | False | True | 0/0/2 | <message FloatValue>; <message FloatValue> |
| `tracks.sharpness.value` | scalar | float | False | False | 0/0/2 | 0.9384632706642151; 0.2330074906349182 |
| `tracks.semantic_confidence` | enum | anduril.sensors.cv.v1.SemanticConfidence | False | False | 0/0/2 | 1; 2 |
| `tracks.tracker_index` | scalar | uint32 | False | False | 0/2/0 | 0; 0 |
| `tracks.disposition` | enum | anduril.ontology.v1.Disposition | False | False | 0/2/0 | 0; 0 |
| `tracks.num_detection_associations` | scalar | uint64 | False | False | 0/0/2 | 27; 4 |
| `tracks.status_code` | enum | anduril.sensors.cv.v1.CVTrackStatusCode | False | False | 0/0/2 | 1; 1 |
| `tracks.unfiltered_class_name` | scalar | string | False | False | 0/0/2 | AIR_VEHICLE; BIRD |
| `tracks.motion_state` | enum | anduril.sensors.cv.v1.ObjectMotionState | False | False | 0/0/2 | 3; 3 |
| `tracks.update_uid` | scalar | string | False | False | 0/0/2 | osDswrfAk2DQt0sgSYsjTx; 09jBMRUgE8hi9XbMhqEHvy |
| `tracks.track_estimate` | message | anduril.sensors.cv.v1.CVStateEstimate | False | True | 0/0/2 | <message CVStateEstimate>; <message CVStateEstimate> |
| `tracks.track_estimate.ptz` | message | anduril.sensors.cv.v1.PanTiltZoom | False | True | 2/0/0 | <message PanTiltZoom>; <message PanTiltZoom> |
| `tracks.track_estimate.ptz.velocity` | message | anduril.type.Vec2f | False | True | 0/0/0 |  |
| `tracks.track_estimate.ptz.velocity.x` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.ptz.velocity.y` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.ptz.position` | message | anduril.type.Vec2f | False | True | 0/0/0 |  |
| `tracks.track_estimate.ptz.position.x` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.ptz.position.y` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.az_el` | message | anduril.sensors.cv.v1.NeuSpherical | False | True | 0/0/2 | <message NeuSpherical>; <message NeuSpherical> |
| `tracks.track_estimate.az_el.position` | message | anduril.type.Vec2f | False | True | 0/0/2 | <message Vec2f>; <message Vec2f> |
| `tracks.track_estimate.az_el.position.x` | scalar | float | False | False | 0/0/2 | 0.8045781850814819; 1.3183249235153198 |
| `tracks.track_estimate.az_el.position.y` | scalar | float | False | False | 0/0/2 | 0.13571196794509888; 0.09642854332923889 |
| `tracks.track_estimate.az_el.velocity` | message | anduril.type.Vec2f | False | True | 0/0/2 | <message Vec2f>; <message Vec2f> |
| `tracks.track_estimate.az_el.velocity.x` | scalar | float | False | False | 0/0/2 | 0.005403326824307442; 0.001500176964327693 |
| `tracks.track_estimate.az_el.velocity.y` | scalar | float | False | False | 0/0/2 | -0.0006875742110423744; 2.8289156034588814e-05 |
| `tracks.track_estimate.az_el.covariance` | message | anduril.type.TMat4f | False | True | 2/0/0 | <message TMat4f>; <message TMat4f> |
| `tracks.track_estimate.az_el.covariance.m00` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.az_el.covariance.m01` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.az_el.covariance.m02` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.az_el.covariance.m03` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.az_el.covariance.m11` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.az_el.covariance.m12` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.az_el.covariance.m13` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.az_el.covariance.m22` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.az_el.covariance.m23` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.az_el.covariance.m33` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.relative` | message | anduril.sensors.cv.v1.CameraRelative | False | True | 2/0/0 | <message CameraRelative>; <message CameraRelative> |
| `tracks.track_estimate.relative.position` | message | anduril.type.Vec2f | False | True | 0/0/0 |  |
| `tracks.track_estimate.relative.position.x` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.relative.position.y` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.relative.velocity` | message | anduril.type.Vec2f | False | True | 0/0/0 |  |
| `tracks.track_estimate.relative.velocity.x` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.relative.velocity.y` | scalar | float | False | False | 0/0/0 |  |
| `tracks.track_estimate.yp_mount` | message | anduril.sensors.cv.v1.YawPitchRelativeToMount | False | True | 2/0/0 | <message YawPitchRelativeToMount>; <message YawPitchRelativeToMount> |
| `tracks.track_estimate.yp_mount.position` | message | anduril.type.YawPitch | False | True | 0/0/0 |  |
| `tracks.track_estimate.yp_mount.position.yaw` | scalar | double | False | False | 0/0/0 |  |
| `tracks.track_estimate.yp_mount.position.pitch` | scalar | double | False | False | 0/0/0 |  |
| `tracks.track_estimate.yp_mount.velocity` | message | anduril.type.YawPitch | False | True | 0/0/0 |  |
| `tracks.track_estimate.yp_mount.velocity.yaw` | scalar | double | False | False | 0/0/0 |  |
| `tracks.track_estimate.yp_mount.velocity.pitch` | scalar | double | False | False | 0/0/0 |  |
| `tracks.track_estimate.yp_mount.camera_relative_velocity` | message | anduril.type.YawPitch | False | True | 0/0/0 |  |
| `tracks.track_estimate.yp_mount.camera_relative_velocity.yaw` | scalar | double | False | False | 0/0/0 |  |
| `tracks.track_estimate.yp_mount.camera_relative_velocity.pitch` | scalar | double | False | False | 0/0/0 |  |
| `tracks.is_manual` | scalar | bool | False | False | 0/2/0 | False; False |
| `tracks.focus_quality` | enum | anduril.sensors.cv.v1.FocusSemanticQuality | False | False | 0/0/2 | 1; 4 |
| `tracks.parent_object_track_id` | message | google.protobuf.UInt64Value | False | True | 2/0/0 | <message UInt64Value>; <message UInt64Value> |
| `tracks.parent_object_track_id.value` | scalar | uint64 | False | False | 0/0/0 |  |
| `tracks.class_distribution` | message | anduril.sensors.cv.v1.ClassDistribution | True | False | 0/0/8 | <message ClassDistribution>; <message ClassDistribution>; <message ClassDistribution> |
| `tracks.class_distribution.classification` | enum | anduril.sensors.cv.v1.ObjectClassification | False | False | 0/0/8 | 21; 11; 50 |
| `tracks.class_distribution.probability_score` | scalar | float | False | False | 0/0/8 | 0.92822265625; 0.00838470458984375; 0.005039215087890625 |
| `assets` | message | anduril.sensors.cv.v1.VisibleAsset | True | False | 0/0/0 |  |
| `assets.asset_id` | scalar | string | False | False | 0/0/0 |  |
| `assets.pos` | message | anduril.type.Vec2 | False | True | 0/0/0 |  |
| `assets.pos.x` | scalar | double | False | False | 0/0/0 |  |
| `assets.pos.y` | scalar | double | False | False | 0/0/0 |  |
| `assets.stddev` | message | anduril.type.TMat2 | False | True | 0/0/0 |  |
| `assets.stddev.mxx` | scalar | double | False | False | 0/0/0 |  |
| `assets.stddev.mxy` | scalar | double | False | False | 0/0/0 |  |
| `assets.stddev.myy` | scalar | double | False | False | 0/0/0 |  |
| `assets.suppressed_detection_ids` | scalar | uint64 | True | False | 0/0/0 |  |
| `assets.mahalanobis_threshold` | scalar | float | False | False | 0/0/0 |  |
| `assets.bounding_box` | message | anduril.sensors.cv.v1.BoundingBox | False | True | 0/0/0 |  |
| `assets.bounding_box.left` | scalar | float | False | False | 0/0/0 |  |
| `assets.bounding_box.top` | scalar | float | False | False | 0/0/0 |  |
| `assets.bounding_box.right` | scalar | float | False | False | 0/0/0 |  |
| `assets.bounding_box.bottom` | scalar | float | False | False | 0/0/0 |  |
| `assets.cov` | message | anduril.type.TMat2 | False | True | 0/0/0 |  |
| `assets.cov.mxx` | scalar | double | False | False | 0/0/0 |  |
| `assets.cov.mxy` | scalar | double | False | False | 0/0/0 |  |
| `assets.cov.myy` | scalar | double | False | False | 0/0/0 |  |

</details>

### `track_states` (channel 2, schema `proto.tower.TrackState`)

- Message encoding / schema encoding: `protobuf` / `protobuf`
- Message count: 11,630
- log_time range (ns): 1761244500017288000 .. 1761245699943885000
- publish_time range (ns): 1761244500017288000 .. 1761245699943885000
- Out-of-order log_time messages: 0
- Sequence behavior: monotonic_increasing=False, increasing_steps=0, equal_steps=11629, decreasing_steps=0, duplicate_sequence_values=1, range=[0, 0]
- Field count (recursive): 261
- Structural samples decoded: 3 (indices [0, 5815, 11629])

**Message structure:** `single_entity_or_update`

No top-level repeated field matches the topic name; top-level scalar identifier-shaped field(s) ['timestamp', 'track_id', 'target_uid', 'track_id2', 'parent_track_id', 'create_timestamp', 'last_measurement_timestamp', 'last_cv_detection_timestamp', 'disposition_timestamp', 'verification_timestamp', 'tower_id', 'tower_id2', 'last_image_detection_id', 'first_cv_detection_timestamp', 'fragment_id'] suggest one message represents one entity/update record, with 13 repeated child/association substructure(s): ['measurements', 'associated_detections', 'sensors', 'track_identity_matches', 'license_plate', 'counts', 'object_class_confidence_distribution', 'max_object_class_confidence', 'identifiers', 'disposition_external', 'object_class_external', 'ranked_camera_feeds', 'signal_summaries'].

**Candidate identifier field statistics (full dataset):**

| field_path | category | populated | null_freq% | distinct | uniqueness_ratio | dup_within_msg (unexpected) | dup_cross_msg (expected) | entities/msg (min/avg/max) |
|---|---|---|---|---|---|---|---|---|
| `associated_detections.topic_id` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `associated_detections.topic_id2` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `atak_contact.uid` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `counts.class_id` | identifier | 0 | 100.0 | 0 | None | 0 | 0 | 0/0.728/4 |
| `counts.sensor_id` | identifier | 0 | 100.0 | 0 | None | 0 | 0 | 0/0.728/4 |
| `counts.source_id` | identifier | 0 | 100.0 | 0 | None | 0 | 0 | 0/0.728/4 |
| `create_timestamp` | timestamp | 11630 | 0.0 | 103 | 0.0089 | 0 | 97 | 1/1.0/1 |
| `disposition_external.track_id` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `disposition_external.track_id2` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `disposition_timestamp` | timestamp | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.0/1 |
| `first_cv_detection_timestamp` | timestamp | 1961 | 0.0 | 11 | 0.0056 | 0 | 11 | 1/1.0/1 |
| `fragment_id` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.0/1 |
| `last_cv_detection_timestamp` | timestamp | 1961 | 0.0 | 1606 | 0.819 | 0 | 52 | 1/1.0/1 |
| `last_image_detection_id` | identifier | 1961 | 0.0 | 1606 | 0.819 | 0 | 52 | 1/1.0/1 |
| `last_measurement_timestamp` | timestamp | 11630 | 0.0 | 11607 | 0.998 | 0 | 23 | 1/1.0/1 |
| `license_plate.detection_id` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `measurements.asset_id` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.031/12 |
| `measurements.asset_id2` | identifier | 11992 | 0.0 | 1 | 0.0001 | 1 | 0 | 1/1.031/12 |
| `measurements.detection_ids` | identifier | 13596 | 0.0 | 1717 | 0.1263 | 65 | 48 | 1/1.169/12 |
| `measurements.sensor_id` | identifier | 11992 | 0.0 | 3 | 0.0003 | 1 | 2 | 1/1.031/12 |
| `measurements.timestamp` | timestamp | 11992 | 0.0 | 11967 | 0.9979 | 0 | 25 | 1/1.031/12 |
| `parent_track_id` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.0/1 |
| `ranked_camera_feeds.asset_id2` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `sensors.asset_id` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.169/2 |
| `sensors.asset_id2` | identifier | 13591 | 0.0 | 1 | 0.0001 | 1 | 0 | 1/1.169/2 |
| `sensors.last_detection_timestamp` | timestamp | 13591 | 0.0 | 11763 | 0.8655 | 0 | 230 | 1/1.169/2 |
| `sensors.sensor_id` | identifier | 13591 | 0.0 | 3 | 0.0002 | 0 | 3 | 1/1.169/2 |
| `target_uid` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.0/1 |
| `timestamp` | timestamp | 11630 | 0.0 | 7254 | 0.6237 | 0 | 2737 | 1/1.0/1 |
| `tower_id` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.0/1 |
| `tower_id2` | identifier | 11630 | 0.0 | 1 | 0.0001 | 0 | 1 | 1/1.0/1 |
| `track_id` | identifier | 11630 | 0.0 | 103 | 0.0089 | 0 | 97 | 1/1.0/1 |
| `track_id2` | identifier | 11630 | 0.0 | 103 | 0.0089 | 0 | 97 | 1/1.0/1 |
| `track_identity_matches.matched_track_id` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `track_identity_matches.matched_track_id2` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `track_identity_matches.source_asset_id2` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `transponder_codes.mode5.mode5_platform_id` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `transponder_codes.mode_s.id` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `verification_timestamp` | timestamp | 1961 | 0.0 | 11 | 0.0056 | 0 | 11 | 1/1.0/1 |

<details><summary>Full recursive field catalog</summary>

| path | kind | type | repeated | presence | observed (null/empty/populated) | sample |
|---|---|---|---|---|---|---|
| `timestamp` | scalar | int64 | False | False | 0/0/3 | 1761244500017288; 1761245072853165; 1761245699943885 |
| `track_id` | scalar | uint64 | False | False | 0/0/3 | 6728857198678527; 8318573655713901; 2580237496223246 |
| `target_uid` | scalar | string | False | False | 0/3/0 | ; ;  |
| `track_id2` | scalar | string | False | False | 0/0/3 | 25295F49158-7aa000016023; 25295F49158-7aa000016065; 25295F49158-7aa000016137 |
| `tracker_software` | enum | proto.tower.TrackerSoftware | False | False | 0/0/3 | 4; 4; 4 |
| `parent_track_id` | scalar | string | False | False | 0/3/0 | ; ;  |
| `track_name` | scalar | string | False | False | 0/3/0 | ; ;  |
| `track_status` | enum | proto.tower.TrackStatus | False | False | 0/0/3 | 3; 2; 2 |
| `create_timestamp` | scalar | int64 | False | False | 0/0/3 | 1761244469821906; 1761244853835520; 1761245681159672 |
| `last_measurement_timestamp` | scalar | int64 | False | False | 0/0/3 | 1761244499966225; 1761245072781915; 1761245699884594 |
| `last_cv_detection_timestamp` | scalar | int64 | False | False | 0/2/1 | 1761244499744630; 0; 0 |
| `disposition_timestamp` | scalar | int64 | False | False | 0/3/0 | 0; 0; 0 |
| `verification_timestamp` | scalar | int64 | False | False | 0/2/1 | 1761244495744722; 0; 0 |
| `enu_pos` | message | proto.tower.ENU | False | True | 0/0/3 | <message ENU>; <message ENU>; <message ENU> |
| `enu_pos.e` | scalar | double | False | False | 0/0/3 | 2.683245140697322e-10; 8.091937678943832e-11; -6.203110761916557e-11 |
| `enu_pos.n` | scalar | double | False | False | 0/0/3 | 3.9331060061640584e-05; 4.0222177003523874e-05; 3.933199419334364e-05 |
| `enu_pos.u` | scalar | double | False | False | 0/0/3 | 1.1504889863837722e-05; 1.2329280233965648e-05; 1.1502664734747111e-05 |
| `lla_pos` | message | proto.tower.LLA | False | True | 3/0/0 | <message LLA>; <message LLA>; <message LLA> |
| `lla_pos.lon` | scalar | double | False | False | 0/0/0 |  |
| `lla_pos.lat` | scalar | double | False | False | 0/0/0 |  |
| `lla_pos.alt` | scalar | double | False | False | 0/0/0 |  |
| `lla_pos.is2d` | scalar | bool | False | False | 0/0/0 |  |
| `lla_pos.altitude_reference` | enum | proto.tower.LLA.AltitudeReference | False | False | 0/0/0 |  |
| `position` | message | anduril.type.v1.LocationGeodetic | False | True | 3/0/0 | <message LocationGeodetic>; <message LocationGeodetic>; <message LocationGeodetic> |
| `position.latitude_degrees` | scalar | double | False | False | 0/0/0 |  |
| `position.longitude_degrees` | scalar | double | False | False | 0/0/0 |  |
| `position.universal_altitude_hae` | message | anduril.type.v1.AltitudeAboveWGS84Ellipsoid | False | True | 0/0/0 |  |
| `position.universal_altitude_hae.provenance` | message | anduril.type.v1.AltitudeProvenance | False | True | 0/0/0 |  |
| `position.universal_altitude_hae.provenance.source_type` | enum | anduril.type.v1.AltitudeProvenanceType | False | False | 0/0/0 |  |
| `position.universal_altitude_hae.value_meters` | scalar | double | False | False | 0/0/0 |  |
| `position.additional_altitudes` | message | anduril.type.v1.Altitude | True | False | 0/0/0 |  |
| `position.additional_altitudes.hae_wgs84` | message | anduril.type.v1.AltitudeAboveWGS84Ellipsoid | False | True | 0/0/0 |  |
| `position.additional_altitudes.hae_wgs84.provenance` | message | anduril.type.v1.AltitudeProvenance | False | True | 0/0/0 |  |
| `position.additional_altitudes.hae_wgs84.provenance.source_type` | enum | anduril.type.v1.AltitudeProvenanceType | False | False | 0/0/0 |  |
| `position.additional_altitudes.hae_wgs84.value_meters` | scalar | double | False | False | 0/0/0 |  |
| `position.additional_altitudes.asf` | message | anduril.type.v1.AltitudeAboveSeaFloor | False | True | 0/0/0 |  |
| `position.additional_altitudes.asf.provenance` | message | anduril.type.v1.AltitudeProvenance | False | True | 0/0/0 |  |
| `position.additional_altitudes.asf.provenance.source_type` | enum | anduril.type.v1.AltitudeProvenanceType | False | False | 0/0/0 |  |
| `position.additional_altitudes.asf.value_meters` | scalar | double | False | False | 0/0/0 |  |
| `position.additional_altitudes.bss` | message | anduril.type.v1.AltitudeBelowSeaSurface | False | True | 0/0/0 |  |
| `position.additional_altitudes.bss.provenance` | message | anduril.type.v1.AltitudeProvenance | False | True | 0/0/0 |  |
| `position.additional_altitudes.bss.provenance.source_type` | enum | anduril.type.v1.AltitudeProvenanceType | False | False | 0/0/0 |  |
| `position.additional_altitudes.bss.value_meters` | scalar | double | False | False | 0/0/0 |  |
| `position.additional_altitudes.pressure_sdp` | message | anduril.type.v1.AltitudeAboveStandardDatumPlanePressure | False | True | 0/0/0 |  |
| `position.additional_altitudes.pressure_sdp.provenance` | message | anduril.type.v1.AltitudeProvenance | False | True | 0/0/0 |  |
| `position.additional_altitudes.pressure_sdp.provenance.source_type` | enum | anduril.type.v1.AltitudeProvenanceType | False | False | 0/0/0 |  |
| `position.additional_altitudes.pressure_sdp.value_meters` | scalar | double | False | False | 0/0/0 |  |
| `position.additional_altitudes.pressure_amsl` | message | anduril.type.v1.AltitudeAboveMeanSeaLevelPressure | False | True | 0/0/0 |  |
| `position.additional_altitudes.pressure_amsl.provenance` | message | anduril.type.v1.AltitudeProvenance | False | True | 0/0/0 |  |
| `position.additional_altitudes.pressure_amsl.provenance.source_type` | enum | anduril.type.v1.AltitudeProvenanceType | False | False | 0/0/0 |  |
| `position.additional_altitudes.pressure_amsl.value_meters` | scalar | double | False | False | 0/0/0 |  |
| `position.additional_altitudes.egm96_amsl` | message | anduril.type.v1.AltitudeAboveMeanSeaLevelEGM96 | False | True | 0/0/0 |  |
| `position.additional_altitudes.egm96_amsl.provenance` | message | anduril.type.v1.AltitudeProvenance | False | True | 0/0/0 |  |
| `position.additional_altitudes.egm96_amsl.provenance.source_type` | enum | anduril.type.v1.AltitudeProvenanceType | False | False | 0/0/0 |  |
| `position.additional_altitudes.egm96_amsl.value_meters` | scalar | double | False | False | 0/0/0 |  |
| `position.additional_altitudes.agl` | message | anduril.type.v1.AltitudeAboveGroundLevel | False | True | 0/0/0 |  |
| `position.additional_altitudes.agl.provenance` | message | anduril.type.v1.AltitudeProvenance | False | True | 0/0/0 |  |
| `position.additional_altitudes.agl.provenance.source_type` | enum | anduril.type.v1.AltitudeProvenanceType | False | False | 0/0/0 |  |
| `position.additional_altitudes.agl.value_meters` | scalar | double | False | False | 0/0/0 |  |
| `enu_vel` | message | proto.tower.ENU | False | True | 0/0/3 | <message ENU>; <message ENU>; <message ENU> |
| `enu_vel.e` | scalar | double | False | False | 0/0/3 | 43.14576514678158; 122.45536295765359; 31.609271194787635 |
| `enu_vel.n` | scalar | double | False | False | 0/0/3 | 5.22915862561904; -172.67732881115685; -23.115891482224672 |
| `enu_vel.u` | scalar | double | False | False | 0/0/3 | 1.6604798089281143; 0.029950387479821927; -1.3046616822289518 |
| `enu_pos_cov` | message | proto.tower.TMat3 | False | True | 0/0/3 | <message TMat3>; <message TMat3>; <message TMat3> |
| `enu_pos_cov.mxx` | scalar | double | False | False | 0/0/3 | 44.82934448736253; 60883.295496880906; 1326.362809255508 |
| `enu_pos_cov.mxy` | scalar | double | False | False | 0/0/3 | 8.905816011658882; -84581.05989652425; -1031.7116382158315 |
| `enu_pos_cov.mxz` | scalar | double | False | False | 0/0/3 | 1.6114548290150366; 14.67034229615058; -312.4718691043231 |
| `enu_pos_cov.myy` | scalar | double | False | False | 0/0/3 | 43.98999783489939; 120171.87136994224; 1017.0730785992082 |
| `enu_pos_cov.myz` | scalar | double | False | False | 0/0/3 | 1.5392739308526189; -20.68701165274716; -362.69239215668614 |
| `enu_pos_cov.mzz` | scalar | double | False | False | 0/0/3 | 36.725797620291374; 902.0354166101283; 3116.46970978685 |
| `enu_vel_cov` | message | proto.tower.TMat3 | False | True | 0/0/3 | <message TMat3>; <message TMat3>; <message TMat3> |
| `enu_vel_cov.mxx` | scalar | double | False | False | 0/0/3 | 29.301564945508396; 400.7124996185303; 66.73043101902596 |
| `enu_vel_cov.mxy` | scalar | double | False | False | 0/0/3 | 17.361204302034544; 3.316285330338117e-15; 0.036667643200282575 |
| `enu_vel_cov.mxz` | scalar | double | False | False | 0/0/3 | 3.9034677294239937; 4.000391464390568e-15; -0.6232383478597908 |
| `enu_vel_cov.myy` | scalar | double | False | False | 0/0/3 | 28.587106455314323; 400.7124996185303; 51.711114422049775 |
| `enu_vel_cov.myz` | scalar | double | False | False | 0/0/3 | 3.8484302863437323; 5.6162449109294815e-15; 1.389198901478721 |
| `enu_vel_cov.mzz` | scalar | double | False | False | 0/0/3 | 14.808891138391798; 400.7124996185303; 139.7195195225392 |
| `enu_accel` | message | proto.tower.ENU | False | True | 3/0/0 | <message ENU>; <message ENU>; <message ENU> |
| `enu_accel.e` | scalar | double | False | False | 0/0/0 |  |
| `enu_accel.n` | scalar | double | False | False | 0/0/0 |  |
| `enu_accel.u` | scalar | double | False | False | 0/0/0 |  |
| `enu_accel_cov` | message | proto.tower.TMat3 | False | True | 3/0/0 | <message TMat3>; <message TMat3>; <message TMat3> |
| `enu_accel_cov.mxx` | scalar | double | False | False | 0/0/0 |  |
| `enu_accel_cov.mxy` | scalar | double | False | False | 0/0/0 |  |
| `enu_accel_cov.mxz` | scalar | double | False | False | 0/0/0 |  |
| `enu_accel_cov.myy` | scalar | double | False | False | 0/0/0 |  |
| `enu_accel_cov.myz` | scalar | double | False | False | 0/0/0 |  |
| `enu_accel_cov.mzz` | scalar | double | False | False | 0/0/0 |  |
| `relative_pos` | message | proto.tower.RelativePosition | False | True | 3/0/0 | <message RelativePosition>; <message RelativePosition>; <message RelativePosition> |
| `relative_pos.relative_pose` | message | anduril.type.Pose | False | True | 0/0/0 |  |
| `relative_pos.relative_pose.pos` | message | anduril.type.LLA | False | True | 0/0/0 |  |
| `relative_pos.relative_pose.pos.lon` | scalar | double | False | False | 0/0/0 |  |
| `relative_pos.relative_pose.pos.lat` | scalar | double | False | False | 0/0/0 |  |
| `relative_pos.relative_pose.pos.alt` | scalar | double | False | False | 0/0/0 |  |
| `relative_pos.relative_pose.pos.is2d` | scalar | bool | False | False | 0/0/0 |  |
| `relative_pos.relative_pose.pos.altitude_reference` | enum | anduril.type.LLA.AltitudeReference | False | False | 0/0/0 |  |
| `relative_pos.relative_pose.att_enu` | message | anduril.type.Quaternion | False | True | 0/0/0 |  |
| `relative_pos.relative_pose.att_enu.x` | scalar | double | False | False | 0/0/0 |  |
| `relative_pos.relative_pose.att_enu.y` | scalar | double | False | False | 0/0/0 |  |
| `relative_pos.relative_pose.att_enu.z` | scalar | double | False | False | 0/0/0 |  |
| `relative_pos.relative_pose.att_enu.w` | scalar | double | False | False | 0/0/0 |  |
| `relative_pos.relative_vertical_error` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `relative_pos.relative_vertical_error.value` | scalar | float | False | False | 0/0/0 |  |
| `relative_pos.relative_horizontal_error` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `relative_pos.relative_horizontal_error.value` | scalar | float | False | False | 0/0/0 |  |
| `relative_pos.slant_range` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `relative_pos.slant_range.value` | scalar | float | False | False | 0/0/0 |  |
| `track_quality` | scalar | uint32 | False | False | 0/3/0 | 0; 0; 0 |
| `object_class` | enum | proto.tower.TrackObjectClass | False | False | 0/0/3 | 4; 4; 4 |
| `object_class_confidence` | scalar | float | False | False | 0/0/3 | 0.9847221970558167; 1.0; 0.9655362963676453 |
| `tower_id` | scalar | uint32 | False | False | 0/3/0 | 0; 0; 0 |
| `tower_id2` | scalar | string | False | False | 0/0/3 | 7aa0; 7aa0; 7aa0 |
| `last_image_detection_id` | scalar | string | False | False | 0/2/1 | X0zFOHL9SO97NqcOt572dc; ;  |
| `measurements` | message | proto.tower.MeasurementAssociation | True | False | 0/0/4 | <message MeasurementAssociation>; <message MeasurementAssociation>; <message MeasurementAssociation> |
| `measurements.timestamp` | scalar | int64 | False | False | 0/0/4 | 1761244499744630; 1761244499966225; 1761245072781915 |
| `measurements.asset_id` | scalar | uint32 | False | False | 0/4/0 | 0; 0; 0 |
| `measurements.asset_id2` | scalar | string | False | False | 0/0/4 | 7aa0; 7aa0; 7aa0 |
| `measurements.sensor_id` | enum | proto.tower.SensorId | False | False | 0/0/4 | 2; 1; 6 |
| `measurements.frame_counter` | scalar | uint64 | False | False | 0/4/0 | 0; 0; 0 |
| `measurements.sensor_index` | scalar | uint32 | False | False | 0/4/0 | 0; 0; 0 |
| `measurements.detection_ids` | scalar | string | True | False | 0/0/5 | cv-7aa0-2-81754; X0zFOHL9SO97NqcOt572dc; radar-7aa0-129676 |
| `associated_detections` | message | proto.tower.AssociatedDetection | True | False | 0/0/0 |  |
| `associated_detections.topic_id` | scalar | uint32 | False | False | 0/0/0 |  |
| `associated_detections.topic_id2` | scalar | string | False | False | 0/0/0 |  |
| `associated_detections.key` | scalar | string | False | False | 0/0/0 |  |
| `associated_detections.detection_indexes` | scalar | uint32 | True | False | 0/0/0 |  |
| `sensors` | message | proto.tower.TrackSensor | True | False | 0/0/4 | <message TrackSensor>; <message TrackSensor>; <message TrackSensor> |
| `sensors.asset_id` | scalar | uint32 | False | False | 0/4/0 | 0; 0; 0 |
| `sensors.asset_id2` | scalar | string | False | False | 0/0/4 | 7aa0; 7aa0; 7aa0 |
| `sensors.sensor_id` | enum | proto.tower.SensorId | False | False | 0/0/4 | 1; 2; 6 |
| `sensors.sensor_index` | scalar | uint32 | False | False | 0/4/0 | 0; 0; 0 |
| `sensors.sensor_descriptor` | scalar | string | False | False | 0/4/0 | ; ;  |
| `sensors.bias` | message | proto.tower.SensorBias | False | True | 4/0/0 | <message SensorBias>; <message SensorBias>; <message SensorBias> |
| `sensors.bias.theta_phi` | message | proto.tower.ThetaPhi | False | True | 0/0/0 |  |
| `sensors.bias.theta_phi.theta` | scalar | double | False | False | 0/0/0 |  |
| `sensors.bias.theta_phi.phi` | scalar | double | False | False | 0/0/0 |  |
| `sensors.detection_count` | scalar | uint64 | False | False | 0/0/4 | 84; 25; 53 |
| `sensors.last_detection_timestamp` | scalar | int64 | False | False | 0/0/4 | 1761244499966225; 1761244499744630; 1761245072781915 |
| `identity` | message | proto.tower.ReIdentificationFeature | False | True | 3/0/0 | <message ReIdentificationFeature>; <message ReIdentificationFeature>; <message ReIdentificationFeature> |
| `identity.identity_descriptor` | scalar | float | True | False | 0/0/0 |  |
| `track_identity_matches` | message | proto.tower.MatchedTrackIdentity | True | False | 0/0/0 |  |
| `track_identity_matches.source_asset_id2` | scalar | string | False | False | 0/0/0 |  |
| `track_identity_matches.matched_track_id` | scalar | uint64 | False | False | 0/0/0 |  |
| `track_identity_matches.matched_track_id2` | scalar | string | False | False | 0/0/0 |  |
| `track_identity_matches.distance` | scalar | float | False | False | 0/0/0 |  |
| `atak_contact` | message | anduril.cot.AtakContact | False | True | 3/0/0 | <message AtakContact>; <message AtakContact>; <message AtakContact> |
| `atak_contact.uid` | scalar | string | False | False | 0/0/0 |  |
| `atak_contact.callsign` | scalar | string | False | False | 0/0/0 |  |
| `license_plate` | message | proto.tower.LicensePlateAssociation | True | False | 0/0/0 |  |
| `license_plate.characters` | scalar | string | False | False | 0/0/0 |  |
| `license_plate.confidence` | enum | proto.tower.DetectionSemanticConfidence | False | False | 0/0/0 |  |
| `license_plate.detection_id` | scalar | string | False | False | 0/0/0 |  |
| `object_descriptor` | scalar | string | False | False | 0/0/3 | Group 3-4,Drone,; Airplane,,; Group 3-4,Drone, |
| `alt_agl` | scalar | double | False | False | 0/0/3 | 658.2872360629353; 10972.775077405533; 695.6397839660285 |
| `counts` | message | proto.tower.TrackerCount | True | False | 0/0/4 | <message TrackerCount>; <message TrackerCount>; <message TrackerCount> |
| `counts.count` | scalar | uint32 | False | False | 0/0/4 | 25; 84; 25 |
| `counts.source_id` | enum | proto.tower.SourceId | False | True | 4/0/0 | 0; 0; 0 |
| `counts.sensor_id` | enum | proto.tower.SensorId | False | True | 4/0/0 | 0; 0; 0 |
| `counts.class_id` | enum | proto.tower.TrackObjectClass | False | True | 4/0/0 | 0; 0; 0 |
| `counts.tracker_internal` | scalar | string | False | True | 0/0/4 | crid:cv_7aa0_81754; crid:radar_129676; cv_detection:AIR_VEHICLE |
| `object_class_confidence_distribution` | message | proto.tower.ObjectClassConfidence | True | False | 0/0/0 |  |
| `object_class_confidence_distribution.class` | enum | proto.tower.TrackObjectClass | False | False | 0/0/0 |  |
| `object_class_confidence_distribution.confidence` | scalar | float | False | False | 0/0/0 |  |
| `max_object_class_confidence` | message | proto.tower.ObjectClassConfidence | True | False | 0/0/0 |  |
| `max_object_class_confidence.class` | enum | proto.tower.TrackObjectClass | False | False | 0/0/0 |  |
| `max_object_class_confidence.confidence` | scalar | float | False | False | 0/0/0 |  |
| `identifiers` | message | anduril.sensors.type.DetectionIdentifier | True | False | 0/0/0 |  |
| `identifiers.key` | scalar | string | False | False | 0/0/0 |  |
| `identifiers.value` | scalar | string | False | False | 0/0/0 |  |
| `identifiers.confidence` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `identifiers.confidence.value` | scalar | float | False | False | 0/0/0 |  |
| `identifiers.source_type` | enum | anduril.sensors.type.IdentifierSource | False | False | 0/0/0 |  |
| `radar_snr` | scalar | float | False | False | 0/3/0 | 0.0; 0.0; 0.0 |
| `rcs` | scalar | float | False | False | 0/1/2 | -3.4443359375; 0.0; -2.9389431476593018 |
| `anomalous_state` | enum | proto.tower.AnomalousState | False | False | 0/3/0 | 0; 0; 0 |
| `disposition` | enum | anduril.ontology.v1.Disposition | False | False | 0/1/2 | 3; 4; 0 |
| `disposition_source` | enum | proto.tower.DispositionSource | False | False | 0/3/0 | 0; 0; 0 |
| `disposition_internal` | enum | anduril.ontology.v1.Disposition | False | False | 0/3/0 | 0; 0; 0 |
| `disposition_external` | message | proto.tower.DispositionState | True | False | 0/0/0 |  |
| `disposition_external.timestamp` | message | google.protobuf.Timestamp | False | True | 0/0/0 |  |
| `disposition_external.timestamp.seconds` | scalar | int64 | False | False | 0/0/0 |  |
| `disposition_external.timestamp.nanos` | scalar | int32 | False | False | 0/0/0 |  |
| `disposition_external.track_id` | scalar | uint64 | False | False | 0/0/0 |  |
| `disposition_external.track_id2` | scalar | string | False | False | 0/0/0 |  |
| `disposition_external.description` | scalar | string | False | False | 0/0/0 |  |
| `disposition_external.hostility_score` | scalar | float | False | False | 0/0/0 |  |
| `disposition_external.disposition` | enum | anduril.ontology.v1.Disposition | False | False | 0/0/0 |  |
| `object_class_internal` | enum | proto.tower.TrackObjectClass | False | False | 0/3/0 | 0; 0; 0 |
| `object_class_external` | message | proto.tower.ObjectClassEntry | True | False | 0/0/0 |  |
| `object_class_external.timestamp` | message | google.protobuf.Timestamp | False | True | 0/0/0 |  |
| `object_class_external.timestamp.seconds` | scalar | int64 | False | False | 0/0/0 |  |
| `object_class_external.timestamp.nanos` | scalar | int32 | False | False | 0/0/0 |  |
| `object_class_external.object_class` | enum | proto.tower.TrackObjectClass | False | False | 0/0/0 |  |
| `estimated_size` | scalar | float | False | False | 0/0/3 | 4.289146423339844; 15.0; 2.2545135021209717 |
| `image_width` | scalar | float | False | False | 0/2/1 | 4.289146423339844; 0.0; 0.0 |
| `image_height` | scalar | float | False | False | 0/2/1 | 2.480504035949707; 0.0; 0.0 |
| `environment` | enum | anduril.ontology.v1.Environment | False | False | 0/0/3 | 1; 1; 1 |
| `transponder_codes` | message | anduril.sensors.type.TransponderCodes | False | True | 3/0/0 | <message TransponderCodes>; <message TransponderCodes>; <message TransponderCodes> |
| `transponder_codes.mode1` | scalar | uint32 | False | False | 0/0/0 |  |
| `transponder_codes.mode2` | scalar | uint32 | False | False | 0/0/0 |  |
| `transponder_codes.mode3` | scalar | uint32 | False | False | 0/0/0 |  |
| `transponder_codes.mode4_interrogation_response` | enum | anduril.sensors.type.InterrogationResponse | False | False | 0/0/0 |  |
| `transponder_codes.mode_s` | message | anduril.sensors.type.ModeS | False | True | 0/0/0 |  |
| `transponder_codes.mode_s.id` | scalar | string | False | False | 0/0/0 |  |
| `transponder_codes.mode_s.address` | scalar | uint32 | False | False | 0/0/0 |  |
| `transponder_codes.mode5` | message | anduril.sensors.type.Mode5 | False | True | 0/0/0 |  |
| `transponder_codes.mode5.mode5_interrogation_response` | enum | anduril.sensors.type.InterrogationResponse | False | False | 0/0/0 |  |
| `transponder_codes.mode5.mode5` | scalar | uint32 | False | False | 0/0/0 |  |
| `transponder_codes.mode5.mode5_platform_id` | scalar | uint32 | False | False | 0/0/0 |  |
| `transponder_codes.mode5.mode5_nationality` | enum | anduril.ontology.v1.Nationality | False | False | 0/0/0 |  |
| `expiration` | message | google.protobuf.Timestamp | False | True | 3/0/0 | <message Timestamp>; <message Timestamp>; <message Timestamp> |
| `expiration.seconds` | scalar | int64 | False | False | 0/0/0 |  |
| `expiration.nanos` | scalar | int32 | False | False | 0/0/0 |  |
| `priority_zone_entered` | enum | proto.tower.PriorityZoneEntered | False | False | 0/3/0 | 0; 0; 0 |
| `first_cv_detection_timestamp` | scalar | int64 | False | False | 0/2/1 | 1761244495744722; 0; 0 |
| `estimated_number_of_objects` | message | proto.tower.EstimatedValue | False | True | 3/0/0 | <message EstimatedValue>; <message EstimatedValue>; <message EstimatedValue> |
| `estimated_number_of_objects.lower_bound` | scalar | float | False | False | 0/0/0 |  |
| `estimated_number_of_objects.upper_bound` | scalar | float | False | False | 0/0/0 |  |
| `triggered_microwave` | scalar | bool | False | False | 0/3/0 | False; False; False |
| `autoid_priority` | scalar | float | False | False | 0/3/0 | 0.0; 0.0; 0.0 |
| `origin_lla` | message | proto.tower.LLA | False | True | 3/0/0 | <message LLA>; <message LLA>; <message LLA> |
| `origin_lla.lon` | scalar | double | False | False | 0/0/0 |  |
| `origin_lla.lat` | scalar | double | False | False | 0/0/0 |  |
| `origin_lla.alt` | scalar | double | False | False | 0/0/0 |  |
| `origin_lla.is2d` | scalar | bool | False | False | 0/0/0 |  |
| `origin_lla.altitude_reference` | enum | proto.tower.LLA.AltitudeReference | False | False | 0/0/0 |  |
| `ranked_camera_feeds` | message | proto.tower.AssetIdSensorIndexPair | True | False | 0/0/0 |  |
| `ranked_camera_feeds.asset_id2` | scalar | string | False | False | 0/0/0 |  |
| `ranked_camera_feeds.sensor_index` | scalar | uint32 | False | False | 0/0/0 |  |
| `ranked_camera_feeds.sensor_quality_score` | scalar | uint32 | False | False | 0/0/0 |  |
| `signal_summaries` | message | proto.tower.SignalSummary | True | False | 0/0/0 |  |
| `signal_summaries.frequency` | message | anduril.sensors.type.v1.IntervalVariate | False | True | 0/0/0 |  |
| `signal_summaries.frequency.value` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.frequency.lower_bound` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.frequency.upper_bound` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.frequency.confidence` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.frequency.support_min` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.frequency.support_max` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_repetition_interval` | message | anduril.sensors.type.v1.IntervalVariate | False | True | 0/0/0 |  |
| `signal_summaries.pulse_repetition_interval.value` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_repetition_interval.lower_bound` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_repetition_interval.upper_bound` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_repetition_interval.confidence` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_repetition_interval.support_min` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_repetition_interval.support_max` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_width` | message | anduril.sensors.type.v1.IntervalVariate | False | True | 0/0/0 |  |
| `signal_summaries.pulse_width.value` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_width.lower_bound` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_width.upper_bound` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_width.confidence` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_width.support_min` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.pulse_width.support_max` | scalar | double | False | False | 0/0/0 |  |
| `signal_summaries.mode` | enum | anduril.sensors.fov.v1.SensorMode | False | False | 0/0/0 |  |
| `activity` | message | proto.tower.Activity | False | True | 3/0/0 | <message Activity>; <message Activity>; <message Activity> |
| `activity.description` | scalar | string | False | False | 0/0/0 |  |
| `emitter_identity` | message | proto.tower.EmitterIdentity | False | True | 3/0/0 | <message EmitterIdentity>; <message EmitterIdentity>; <message EmitterIdentity> |
| `emitter_identity.elnot` | message | google.protobuf.StringValue | False | True | 0/0/0 |  |
| `emitter_identity.elnot.value` | scalar | string | False | False | 0/0/0 |  |
| `emitter_identity.cenot` | message | google.protobuf.StringValue | False | True | 0/0/0 |  |
| `emitter_identity.cenot.value` | scalar | string | False | False | 0/0/0 |  |
| `fragment_id` | scalar | uint32 | False | False | 0/3/0 | 0; 0; 0 |

</details>

### `cv_detections` (channel 3, schema `anduril.sensors.cv.v1.CVDetectionFrame`)

- Message encoding / schema encoding: `protobuf` / `protobuf`
- Message count: 7,121
- log_time range (ns): 1761244500078338000 .. 1761245699881083000
- publish_time range (ns): 1761244500078338000 .. 1761245699881083000
- Out-of-order log_time messages: 0
- Sequence behavior: monotonic_increasing=False, increasing_steps=0, equal_steps=7120, decreasing_steps=0, duplicate_sequence_values=1, range=[0, 0]
- Field count (recursive): 117
- Structural samples decoded: 3 (indices [0, 3560, 7120])

**Message structure:** `batch_of_entities`

Top-level repeated field 'detections' shares its name with the topic 'cv_detections', so each message appears to be a batch/frame containing multiple entities of that type. Companion repeated field(s) also present: ['detectors', 'assets'].

**Candidate identifier field statistics (full dataset):**

| field_path | category | populated | null_freq% | distinct | uniqueness_ratio | dup_within_msg (unexpected) | dup_cross_msg (expected) | entities/msg (min/avg/max) |
|---|---|---|---|---|---|---|---|---|
| `assets.asset_id` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `assets.suppressed_detection_ids` | identifier | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `detections.detection_id` | identifier | 1911 | 0.0 | 1911 | 1.0 | 0 | 0 | 0/0.268/2 |
| `detections.detection_uid` | identifier | 1911 | 0.0 | 1911 | 1.0 | 0 | 0 | 0/0.268/2 |
| `detectors.detector_id` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.0/1 |
| `metadata.sensor_id` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.0/1 |

<details><summary>Full recursive field catalog</summary>

| path | kind | type | repeated | presence | observed (null/empty/populated) | sample |
|---|---|---|---|---|---|---|
| `capture_time` | message | google.protobuf.Timestamp | False | True | 0/0/3 | <message Timestamp>; <message Timestamp>; <message Timestamp> |
| `capture_time.seconds` | scalar | int64 | False | False | 0/0/3 | 1761244500; 1761245099; 1761245699 |
| `capture_time.nanos` | scalar | int32 | False | False | 0/0/3 | 78338000; 112276000; 881083000 |
| `metadata` | message | anduril.sensors.cv.v1.ImageFrameMetadata | False | True | 0/0/3 | <message ImageFrameMetadata>; <message ImageFrameMetadata>; <message ImageFrameMetadata> |
| `metadata.sensor_id` | scalar | string | False | False | 0/3/0 | ; ;  |
| `metadata.image_width` | scalar | uint32 | False | False | 0/0/3 | 1280; 1280; 1280 |
| `metadata.image_height` | scalar | uint32 | False | False | 0/0/3 | 1024; 1024; 1024 |
| `metadata.horizontal_fov_deg` | scalar | float | False | False | 0/0/3 | 0.8148589134216309; 0.8148589134216309; 0.8148589134216309 |
| `metadata.vertical_fov_deg` | scalar | float | False | False | 0/0/3 | 0.6518911123275757; 0.6518911123275757; 0.6518911123275757 |
| `metadata.focal_length` | scalar | float | False | False | 0/3/0 | 0.0; 0.0; 0.0 |
| `metadata.focus` | scalar | float | False | False | 0/0/3 | 33071.0; 32708.0; 33091.0 |
| `metadata.spectrum` | enum | anduril.sensors.cv.v1.ImageSpectrum | False | False | 0/0/3 | 3; 3; 3 |
| `metadata.pinhole` | message | anduril.sensors.cv.v1.CameraIntrinsicsPinhole | False | True | 3/0/0 | <message CameraIntrinsicsPinhole>; <message CameraIntrinsicsPinhole>; <message CameraIntrinsicsPinhole> |
| `metadata.pinhole.fx` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pinhole.fy` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pinhole.cx` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pinhole.cy` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pinhole.s` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general` | message | anduril.sensors.cv.v1.CameraIntrinsicsGeneral | False | True | 3/0/0 | <message CameraIntrinsicsGeneral>; <message CameraIntrinsicsGeneral>; <message CameraIntrinsicsGeneral> |
| `metadata.general.r1` | message | anduril.type.Vec3 | False | True | 0/0/0 |  |
| `metadata.general.r1.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r1.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r1.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r2` | message | anduril.type.Vec3 | False | True | 0/0/0 |  |
| `metadata.general.r2.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r2.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r2.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r3` | message | anduril.type.Vec3 | False | True | 0/0/0 |  |
| `metadata.general.r3.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r3.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.general.r3.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pose` | message | anduril.type.Pose | False | True | 0/0/3 | <message Pose>; <message Pose>; <message Pose> |
| `metadata.pose.pos` | message | anduril.type.LLA | False | True | 3/0/0 | <message LLA>; <message LLA>; <message LLA> |
| `metadata.pose.pos.lon` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pose.pos.lat` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pose.pos.alt` | scalar | double | False | False | 0/0/0 |  |
| `metadata.pose.pos.is2d` | scalar | bool | False | False | 0/0/0 |  |
| `metadata.pose.pos.altitude_reference` | enum | anduril.type.LLA.AltitudeReference | False | False | 0/0/0 |  |
| `metadata.pose.att_enu` | message | anduril.type.Quaternion | False | True | 0/0/3 | <message Quaternion>; <message Quaternion>; <message Quaternion> |
| `metadata.pose.att_enu.x` | scalar | double | False | False | 0/0/3 | -0.02262306000250667; -0.0036349426353292267; -0.01638493410033311 |
| `metadata.pose.att_enu.y` | scalar | double | False | False | 0/0/3 | 0.06396143603745993; 0.04835643883919667; 0.022347448517745835 |
| `metadata.pose.att_enu.z` | scalar | double | False | False | 0/0/3 | -0.3729498749319718; -0.1259323679012978; -0.6575720634939458 |
| `metadata.pose.att_enu.w` | scalar | double | False | False | 0/0/3 | 0.9253677769645836; 0.9908529056977132; 0.752881867753228 |
| `metadata.camera_pose` | message | anduril.type.Pose | False | True | 0/0/3 | <message Pose>; <message Pose>; <message Pose> |
| `metadata.camera_pose.pos` | message | anduril.type.LLA | False | True | 3/0/0 | <message LLA>; <message LLA>; <message LLA> |
| `metadata.camera_pose.pos.lon` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_pose.pos.lat` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_pose.pos.alt` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_pose.pos.is2d` | scalar | bool | False | False | 0/0/0 |  |
| `metadata.camera_pose.pos.altitude_reference` | enum | anduril.type.LLA.AltitudeReference | False | False | 0/0/0 |  |
| `metadata.camera_pose.att_enu` | message | anduril.type.Quaternion | False | True | 0/0/3 | <message Quaternion>; <message Quaternion>; <message Quaternion> |
| `metadata.camera_pose.att_enu.x` | scalar | double | False | False | 0/0/3 | 0.022623060002506672; 0.0036349426353292254; 0.016384934100333103 |
| `metadata.camera_pose.att_enu.y` | scalar | double | False | False | 0/0/3 | -0.06396143603745995; -0.04835643883919666; -0.022347448517745824 |
| `metadata.camera_pose.att_enu.z` | scalar | double | False | False | 0/0/3 | 0.37294987493197185; 0.12593236790129775; 0.6575720634939455 |
| `metadata.camera_pose.att_enu.w` | scalar | double | False | False | 0/0/3 | 0.9253677769645838; 0.9908529056977129; 0.7528818677532276 |
| `metadata.camera_orientation_to_mount` | message | anduril.type.Quaternion | False | True | 3/0/0 | <message Quaternion>; <message Quaternion>; <message Quaternion> |
| `metadata.camera_orientation_to_mount.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_orientation_to_mount.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_orientation_to_mount.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.camera_orientation_to_mount.w` | scalar | double | False | False | 0/0/0 |  |
| `metadata.frame_number` | scalar | uint64 | False | False | 0/0/3 | 3052846; 3070817; 3088840 |
| `metadata.sensor_index` | scalar | uint32 | False | False | 0/0/3 | 2; 2; 2 |
| `metadata.mount_name` | message | google.protobuf.StringValue | False | True | 0/0/3 | <message StringValue>; <message StringValue>; <message StringValue> |
| `metadata.mount_name.value` | scalar | string | False | False | 0/0/3 | PTU; PTU; PTU |
| `metadata.camera_name` | message | google.protobuf.StringValue | False | True | 0/0/3 | <message StringValue>; <message StringValue>; <message StringValue> |
| `metadata.camera_name.value` | scalar | string | False | False | 0/0/3 | MWIR; MWIR; MWIR |
| `detectors` | message | anduril.sensors.cv.v1.CVDetectorMetadata | True | False | 0/0/3 | <message CVDetectorMetadata>; <message CVDetectorMetadata>; <message CVDetectorMetadata> |
| `detectors.detector_id` | scalar | string | False | False | 0/3/0 | ; ;  |
| `detectors.detector_type` | scalar | string | False | False | 0/0/3 | DetectorTRT; DetectorTRT; DetectorTRT |
| `detections` | message | anduril.sensors.cv.v1.CVDetection | True | False | 0/0/2 | <message CVDetection>; <message CVDetection> |
| `detections.class_name` | scalar | string | False | False | 0/0/2 | AIR_VEHICLE; BIRD |
| `detections.object_class` | enum | anduril.sensors.cv.v1.ObjectClassification | False | False | 0/0/2 | 21; 11 |
| `detections.bounding_box` | message | anduril.sensors.cv.v1.BoundingBox | False | True | 0/0/2 | <message BoundingBox>; <message BoundingBox> |
| `detections.bounding_box.left` | scalar | float | False | False | 0/0/2 | 0.515625; 0.5322265625 |
| `detections.bounding_box.top` | scalar | float | False | False | 0/0/2 | 0.49102783203125; 0.53924560546875 |
| `detections.bounding_box.right` | scalar | float | False | False | 0/0/2 | 0.5849609375; 0.548828125 |
| `detections.bounding_box.bottom` | scalar | float | False | False | 0/0/2 | 0.53436279296875; 0.55694580078125 |
| `detections.score` | scalar | float | False | False | 0/0/2 | 0.91845703125; 0.447998046875 |
| `detections.semantic_confidence` | enum | anduril.sensors.cv.v1.SemanticConfidence | False | False | 0/0/2 | 1; 2 |
| `detections.detector_index` | scalar | uint32 | False | False | 0/2/0 | 0; 0 |
| `detections.detection_id` | scalar | uint64 | False | False | 0/0/2 | 81781; 82993 |
| `detections.detection_uid` | scalar | string | False | False | 0/0/2 | RtWzTz6D0T74wkgAIT1B3Q; J73ev3o49HIKtpv5sZ1pTv |
| `detections.disposition` | enum | anduril.ontology.v1.Disposition | False | False | 0/2/0 | 0; 0 |
| `detections.motion_state` | enum | anduril.sensors.cv.v1.ObjectMotionState | False | False | 0/0/2 | 1; 1 |
| `detections.focus_score` | message | google.protobuf.FloatValue | False | True | 0/0/2 | <message FloatValue>; <message FloatValue> |
| `detections.focus_score.value` | scalar | float | False | False | 0/0/2 | 0.06954175233840942; 0.7669925093650818 |
| `detections.sharpness` | message | google.protobuf.FloatValue | False | True | 0/0/2 | <message FloatValue>; <message FloatValue> |
| `detections.sharpness.value` | scalar | float | False | False | 0/0/2 | 0.9304582476615906; 0.2330074906349182 |
| `detections.crop_edge_size` | message | google.protobuf.Int32Value | False | True | 0/0/2 | <message Int32Value>; <message Int32Value> |
| `detections.crop_edge_size.value` | scalar | int32 | False | False | 0/0/2 | 89; 22 |
| `detections.mean_lc` | message | google.protobuf.DoubleValue | False | True | 0/0/2 | <message DoubleValue>; <message DoubleValue> |
| `detections.mean_lc.value` | scalar | double | False | False | 0/0/2 | 0.7299595883633327; 0.6700255457034782 |
| `detections.focus_quality` | enum | anduril.sensors.cv.v1.FocusSemanticQuality | False | False | 0/0/2 | 1; 4 |
| `detections.parent_object_detection_id` | message | google.protobuf.UInt64Value | False | True | 2/0/0 | <message UInt64Value>; <message UInt64Value> |
| `detections.parent_object_detection_id.value` | scalar | uint64 | False | False | 0/0/0 |  |
| `detections.static_suppression_label` | message | anduril.sensors.cv.v1.StaticSuppressionLabel | False | True | 2/0/0 | <message StaticSuppressionLabel>; <message StaticSuppressionLabel> |
| `detections.static_suppression_label.suppressed_region` | scalar | bool | False | False | 0/0/0 |  |
| `assets` | message | anduril.sensors.cv.v1.VisibleAsset | True | False | 0/0/0 |  |
| `assets.asset_id` | scalar | string | False | False | 0/0/0 |  |
| `assets.pos` | message | anduril.type.Vec2 | False | True | 0/0/0 |  |
| `assets.pos.x` | scalar | double | False | False | 0/0/0 |  |
| `assets.pos.y` | scalar | double | False | False | 0/0/0 |  |
| `assets.stddev` | message | anduril.type.TMat2 | False | True | 0/0/0 |  |
| `assets.stddev.mxx` | scalar | double | False | False | 0/0/0 |  |
| `assets.stddev.mxy` | scalar | double | False | False | 0/0/0 |  |
| `assets.stddev.myy` | scalar | double | False | False | 0/0/0 |  |
| `assets.suppressed_detection_ids` | scalar | uint64 | True | False | 0/0/0 |  |
| `assets.mahalanobis_threshold` | scalar | float | False | False | 0/0/0 |  |
| `assets.bounding_box` | message | anduril.sensors.cv.v1.BoundingBox | False | True | 0/0/0 |  |
| `assets.bounding_box.left` | scalar | float | False | False | 0/0/0 |  |
| `assets.bounding_box.top` | scalar | float | False | False | 0/0/0 |  |
| `assets.bounding_box.right` | scalar | float | False | False | 0/0/0 |  |
| `assets.bounding_box.bottom` | scalar | float | False | False | 0/0/0 |  |
| `assets.cov` | message | anduril.type.TMat2 | False | True | 0/0/0 |  |
| `assets.cov.mxx` | scalar | double | False | False | 0/0/0 |  |
| `assets.cov.mxy` | scalar | double | False | False | 0/0/0 |  |
| `assets.cov.myy` | scalar | double | False | False | 0/0/0 |  |

</details>

### `radar_detections` (channel 4, schema `anduril.sensors.radar.v1.RadarFrame`)

- Message encoding / schema encoding: `protobuf` / `protobuf`
- Message count: 2,902
- log_time range (ns): 1761244500152824000 .. 1761245699884594000
- publish_time range (ns): 1761244500152824000 .. 1761245699884594000
- Out-of-order log_time messages: 0
- Sequence behavior: monotonic_increasing=False, increasing_steps=0, equal_steps=2901, decreasing_steps=0, duplicate_sequence_values=1, range=[0, 0]
- Field count (recursive): 223
- Structural samples decoded: 3 (indices [0, 1451, 2901])

**Message structure:** `batch_of_entities`

Top-level repeated field 'detections' shares its name with the topic 'radar_detections', so each message appears to be a batch/frame containing multiple entities of that type.

**Radar detection-vs-track discrimination:**

No separate top-level repeated field for radar tracks was found. Instead, each detection record carries an inline track-association field: ['detections.track_id']. This means, in the observed data, radar detections and their track association live in the SAME record -- there is no distinct 'radar track' message type/topic.

**Candidate identifier field statistics (full dataset):**

| field_path | category | populated | null_freq% | distinct | uniqueness_ratio | dup_within_msg (unexpected) | dup_cross_msg (expected) | entities/msg (min/avg/max) |
|---|---|---|---|---|---|---|---|---|
| `asset_id` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.0/1 |
| `asset_id2` | identifier | 2902 | 0.0 | 1 | 0.0003 | 0 | 1 | 1/1.0/1 |
| `detections.debug.rada_v6_debug.desired_revisit_time` | timestamp | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `detections.debug.rada_v6_debug.optimal_revisit_time` | timestamp | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `detections.detection_metadata.echoshield.lifetime` | timestamp | 0 | None | 0 | None | 0 | 0 | 0/0.0/0 |
| `detections.track_id` | identifier | 2929 | 0.0 | 81 | 0.0277 | 0 | 73 | 1/1.009/2 |
| `id` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.0/1 |
| `metadata.sensor_id` | identifier | 0 | 0.0 | 0 | None | 0 | 0 | 1/1.0/1 |

<details><summary>Full recursive field catalog</summary>

| path | kind | type | repeated | presence | observed (null/empty/populated) | sample |
|---|---|---|---|---|---|---|
| `metadata` | message | anduril.sensors.radar.v1.RadarFrameMetadata | False | True | 0/0/3 | <message RadarFrameMetadata>; <message RadarFrameMetadata>; <message RadarFrameMetadata> |
| `metadata.sensor_id` | scalar | string | False | False | 0/3/0 | ; ;  |
| `metadata.mount_pose` | message | anduril.sensors.mount.v1.MountPointPose | False | True | 3/0/0 | <message MountPointPose>; <message MountPointPose>; <message MountPointPose> |
| `metadata.mount_pose.location` | message | anduril.type.LLA | False | True | 0/0/0 |  |
| `metadata.mount_pose.location.lon` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.location.lat` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.location.alt` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.location.is2d` | scalar | bool | False | False | 0/0/0 |  |
| `metadata.mount_pose.location.altitude_reference` | enum | anduril.type.LLA.AltitudeReference | False | False | 0/0/0 |  |
| `metadata.mount_pose.location_uncertainty` | message | anduril.type.TMat3 | False | True | 0/0/0 |  |
| `metadata.mount_pose.location_uncertainty.mxx` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.location_uncertainty.mxy` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.location_uncertainty.mxz` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.location_uncertainty.myy` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.location_uncertainty.myz` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.location_uncertainty.mzz` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.absolute` | message | anduril.sensors.mount.v1.MountPointPose.AbsoluteOrientation | False | True | 0/0/0 |  |
| `metadata.mount_pose.absolute.mountToEnu` | message | anduril.type.Quaternion | False | True | 0/0/0 |  |
| `metadata.mount_pose.absolute.mountToEnu.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.absolute.mountToEnu.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.absolute.mountToEnu.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.absolute.mountToEnu.w` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.relative` | message | anduril.sensors.mount.v1.MountPointPose.RelativeOrientation | False | True | 0/0/0 |  |
| `metadata.mount_pose.relative.bodyToEnu` | message | anduril.type.Quaternion | False | True | 0/0/0 |  |
| `metadata.mount_pose.relative.bodyToEnu.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.relative.bodyToEnu.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.relative.bodyToEnu.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.relative.bodyToEnu.w` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.relative.mountToBody` | message | anduril.type.Quaternion | False | True | 0/0/0 |  |
| `metadata.mount_pose.relative.mountToBody.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.relative.mountToBody.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.relative.mountToBody.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.mount_pose.relative.mountToBody.w` | scalar | double | False | False | 0/0/0 |  |
| `metadata.beam_scan` | message | anduril.sensors.radar.v1.BeamScan | False | True | 3/0/0 | <message BeamScan>; <message BeamScan>; <message BeamScan> |
| `metadata.beam_scan.center_vector` | message | anduril.type.Vec3 | False | True | 0/0/0 |  |
| `metadata.beam_scan.center_vector.x` | scalar | double | False | False | 0/0/0 |  |
| `metadata.beam_scan.center_vector.y` | scalar | double | False | False | 0/0/0 |  |
| `metadata.beam_scan.center_vector.z` | scalar | double | False | False | 0/0/0 |  |
| `metadata.beam_scan.size` | message | anduril.sensors.radar.v1.BeamScan.Size | False | True | 0/0/0 |  |
| `metadata.beam_scan.size.width` | scalar | double | False | False | 0/0/0 |  |
| `metadata.beam_scan.size.height` | scalar | double | False | False | 0/0/0 |  |
| `metadata.radial_area_scan` | message | anduril.sensors.radar.v1.RadialAreaScan | False | True | 3/0/0 | <message RadialAreaScan>; <message RadialAreaScan>; <message RadialAreaScan> |
| `metadata.radial_area_scan.azimuth_range` | message | anduril.type.DoubleRange | False | True | 0/0/0 |  |
| `metadata.radial_area_scan.azimuth_range.min` | scalar | double | False | False | 0/0/0 |  |
| `metadata.radial_area_scan.azimuth_range.max` | scalar | double | False | False | 0/0/0 |  |
| `metadata.radial_area_scan.elevation_range` | message | anduril.type.DoubleRange | False | True | 0/0/0 |  |
| `metadata.radial_area_scan.elevation_range.min` | scalar | double | False | False | 0/0/0 |  |
| `metadata.radial_area_scan.elevation_range.max` | scalar | double | False | False | 0/0/0 |  |
| `metadata.radar_type` | enum | anduril.sensors.radar.v1.RadarType | False | False | 0/3/0 | 0; 0; 0 |
| `detections` | message | anduril.sensors.radar.v1.RadarDetection | True | False | 0/0/3 | <message RadarDetection>; <message RadarDetection>; <message RadarDetection> |
| `detections.range` | scalar | double | False | False | 0/3/0 | 0.0; 0.0; 0.0 |
| `detections.azimuth` | scalar | double | False | False | 0/0/3 | 0.7604607509735206; 1.2767821268320307; 0.8601361035087817 |
| `detections.elevation` | message | google.protobuf.DoubleValue | False | True | 0/0/3 | <message DoubleValue>; <message DoubleValue>; <message DoubleValue> |
| `detections.elevation.value` | scalar | double | False | False | 0/0/3 | 0.13140181748094548; 0.029508657595159082; 0.1544125527568858 |
| `detections.range_rate` | message | google.protobuf.DoubleValue | False | True | 3/0/0 | <message DoubleValue>; <message DoubleValue>; <message DoubleValue> |
| `detections.range_rate.value` | scalar | double | False | False | 0/0/0 |  |
| `detections.return_strength` | message | google.protobuf.DoubleValue | False | True | 3/0/0 | <message DoubleValue>; <message DoubleValue>; <message DoubleValue> |
| `detections.return_strength.value` | scalar | double | False | False | 0/0/0 |  |
| `detections.snr` | message | google.protobuf.DoubleValue | False | True | 3/0/0 | <message DoubleValue>; <message DoubleValue>; <message DoubleValue> |
| `detections.snr.value` | scalar | double | False | False | 0/0/0 |  |
| `detections.object_type` | message | anduril.ontology.v1.ObjectType | False | True | 3/0/0 | <message ObjectType>; <message ObjectType>; <message ObjectType> |
| `detections.object_type.class` | enum | anduril.ontology.v1.Class | False | False | 0/0/0 |  |
| `detections.object_type.disposition` | enum | anduril.ontology.v1.Disposition | False | False | 0/0/0 |  |
| `detections.object_type.environment` | enum | anduril.ontology.v1.Environment | False | False | 0/0/0 |  |
| `detections.track_id` | scalar | string | False | False | 0/0/3 | 129676; 129774; 129888 |
| `detections.azimuth_sigma` | message | google.protobuf.DoubleValue | False | True | 0/0/3 | <message DoubleValue>; <message DoubleValue>; <message DoubleValue> |
| `detections.azimuth_sigma.value` | scalar | double | False | False | 0/0/3 | 0.009847021661698818; 0.009540374390780926; 0.009890515357255936 |
| `detections.elevation_sigma` | message | google.protobuf.DoubleValue | False | True | 0/0/3 | <message DoubleValue>; <message DoubleValue>; <message DoubleValue> |
| `detections.elevation_sigma.value` | scalar | double | False | False | 0/0/3 | 0.009999854490160942; 0.009990543127059937; 0.00999999139457941 |
| `detections.filter_type` | enum | anduril.sensors.radar.v1.RadarDetection.FilterType | False | False | 0/3/0 | 0; 0; 0 |
| `detections.approx_lla` | message | anduril.type.LLA | False | True | 3/0/0 | <message LLA>; <message LLA>; <message LLA> |
| `detections.approx_lla.lon` | scalar | double | False | False | 0/0/0 |  |
| `detections.approx_lla.lat` | scalar | double | False | False | 0/0/0 |  |
| `detections.approx_lla.alt` | scalar | double | False | False | 0/0/0 |  |
| `detections.approx_lla.is2d` | scalar | bool | False | False | 0/0/0 |  |
| `detections.approx_lla.altitude_reference` | enum | anduril.type.LLA.AltitudeReference | False | False | 0/0/0 |  |
| `detections.object_class` | enum | proto.tower.TrackObjectClass | False | False | 0/0/3 | 12; 12; 12 |
| `detections.range_sigma` | message | google.protobuf.DoubleValue | False | True | 0/0/3 | <message DoubleValue>; <message DoubleValue>; <message DoubleValue> |
| `detections.range_sigma.value` | scalar | double | False | False | 0/0/3 | 2.0; 2.0; 2.0 |
| `detections.range_rate_sigma` | message | google.protobuf.DoubleValue | False | True | 0/0/3 | <message DoubleValue>; <message DoubleValue>; <message DoubleValue> |
| `detections.range_rate_sigma.value` | scalar | double | False | False | 0/0/3 | 0.3059280812740326; 0.3488037884235382; 0.3059280812740326 |
| `detections.debug` | message | anduril.sensors.radar.v1.DetectionDebugParameters | False | True | 3/0/0 | <message DetectionDebugParameters>; <message DetectionDebugParameters>; <message DetectionDebugParameters> |
| `detections.debug.rada_v6_debug` | message | anduril.sensors.radar.v1.RadaV6 | False | True | 0/0/0 |  |
| `detections.debug.rada_v6_debug.desired_revisit_time` | scalar | uint32 | False | False | 0/0/0 |  |
| `detections.debug.rada_v6_debug.optimal_revisit_time` | scalar | uint32 | False | False | 0/0/0 |  |
| `detections.debug.rada_v6_debug.track_in_search` | scalar | uint32 | False | False | 0/0/0 |  |
| `detections.debug.rada_v6_debug.num_ebf_tracks` | scalar | uint32 | False | False | 0/0/0 |  |
| `detections.debug.rada_v6_debug.pre_ebf_up` | scalar | uint32 | False | False | 0/0/0 |  |
| `detections.debug.rada_v6_debug.pre_ebf_el` | scalar | uint32 | False | False | 0/0/0 |  |
| `detections.spatial_kinematics` | message | anduril.sensors.radar.v1.SpatialKinematics | False | True | 3/0/0 | <message SpatialKinematics>; <message SpatialKinematics>; <message SpatialKinematics> |
| `detections.spatial_kinematics.ecef_pos` | message | proto.tower.ECEF | False | True | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_pos.x` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_pos.y` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_pos.z` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_vel` | message | proto.tower.ECEF | False | True | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_vel.x` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_vel.y` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_vel.z` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_pos_cov` | message | proto.tower.TMat3 | False | True | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_pos_cov.mxx` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_pos_cov.mxy` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_pos_cov.mxz` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_pos_cov.myy` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_pos_cov.myz` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_pos_cov.mzz` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_vel_cov` | message | proto.tower.TMat3 | False | True | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_vel_cov.mxx` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_vel_cov.mxy` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_vel_cov.mxz` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_vel_cov.myy` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_vel_cov.myz` | scalar | double | False | False | 0/0/0 |  |
| `detections.spatial_kinematics.ecef_vel_cov.mzz` | scalar | double | False | False | 0/0/0 |  |
| `detections.estimated_width_meters` | message | google.protobuf.DoubleValue | False | True | 3/0/0 | <message DoubleValue>; <message DoubleValue>; <message DoubleValue> |
| `detections.estimated_width_meters.value` | scalar | double | False | False | 0/0/0 |  |
| `detections.is_marked` | scalar | bool | False | False | 0/3/0 | False; False; False |
| `detections.panel_id` | message | google.protobuf.Int32Value | False | True | 3/0/0 | <message Int32Value>; <message Int32Value>; <message Int32Value> |
| `detections.panel_id.value` | scalar | int32 | False | False | 0/0/0 |  |
| `detections.detection_metadata` | message | anduril.sensors.radar.v1.RadarDetectionMetadata | False | True | 3/0/0 | <message RadarDetectionMetadata>; <message RadarDetectionMetadata>; <message RadarDetectionMetadata> |
| `detections.detection_metadata.echoshield` | message | anduril.sensors.radar.v1.EchoshieldDetectionMetdata | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.state` | scalar | uint32 | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.lifetime` | scalar | uint32 | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.confidence_level` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.confidence_level.value` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.xyz_est` | message | anduril.type.Vec3 | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.xyz_est.x` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.xyz_est.y` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.xyz_est.z` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_xyz_est` | message | anduril.type.Vec3 | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_xyz_est.x` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_xyz_est.y` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_xyz_est.z` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.ecef_est` | message | proto.tower.ECEF | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.ecef_est.x` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.ecef_est.y` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.ecef_est.z` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_ecef_est` | message | proto.tower.ECEF | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_ecef_est.x` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_ecef_est.y` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_ecef_est.z` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.enu_est` | message | anduril.type.ENU | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.enu_est.e` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.enu_est.n` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.enu_est.u` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_enu_est` | message | anduril.type.ENU | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_enu_est.e` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_enu_est.n` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.vel_enu_est.u` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.rcs_est` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.rcs_est.value` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.distance_of_closest_approach` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.distance_of_closest_approach.value` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.prob_unknown` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.prob_unknown.value` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.prob_uav` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.prob_uav.value` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.last_update_time` | message | google.protobuf.Timestamp | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.last_update_time.seconds` | scalar | int64 | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.last_update_time.nanos` | scalar | int32 | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.last_assoc_time` | message | google.protobuf.Timestamp | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.last_assoc_time.seconds` | scalar | int64 | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.last_assoc_time.nanos` | scalar | int32 | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.time_of_closest_approach` | message | google.protobuf.Timestamp | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.time_of_closest_approach.seconds` | scalar | int64 | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.time_of_closest_approach.nanos` | scalar | int32 | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.acquired_time` | message | google.protobuf.Timestamp | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.acquired_time.seconds` | scalar | int64 | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.acquired_time.nanos` | scalar | int32 | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.class_probabilities` | message | anduril.sensors.radar.v1.EchoshieldClassProbability | True | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.class_probabilities.class_type` | enum | anduril.sensors.radar.v1.EchoshieldClassMapping | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.class_probabilities.probability` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended` | message | anduril.sensors.radar.v1.EchoshieldExtendedMessage | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.agl_est` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.agl_est.value` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.prob_agl_roi` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.prob_agl_roi.value` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.prob_clf_agl_roi` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.prob_clf_agl_roi.value` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.prob_clf_speed_roi` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.prob_clf_speed_roi.value` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.prob_clf_rcs_roi` | message | google.protobuf.FloatValue | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.prob_clf_rcs_roi.value` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance` | message | anduril.type.TMat6 | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mxx` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mxy` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mxz` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mxu` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mxv` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mxw` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.myy` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.myz` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.myu` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.myv` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.myw` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mzz` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mzu` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mzv` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mzw` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.muu` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.muv` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.muw` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mvv` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mvw` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_covariance.mww` | scalar | double | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_innovation_covariance` | message | anduril.type.TMat4f | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_innovation_covariance.m00` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_innovation_covariance.m01` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_innovation_covariance.m02` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_innovation_covariance.m03` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_innovation_covariance.m11` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_innovation_covariance.m12` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_innovation_covariance.m13` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_innovation_covariance.m22` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_innovation_covariance.m23` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.state_innovation_covariance.m33` | scalar | float | False | False | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.assoc_meas_chi2` | message | anduril.sensors.radar.v1.EchoshieldExtendedMessage.Chi2 | False | True | 0/0/0 |  |
| `detections.detection_metadata.echoshield.extended.assoc_meas_chi2.values` | scalar | float | True | False | 0/0/0 |  |
| `detections.cluster` | message | anduril.sensors.radar.v1.RadarDetection | True | False | 0/0/0 |  |
| `id` | scalar | string | False | False | 0/3/0 | ; ;  |
| `capture_time` | message | google.protobuf.Timestamp | False | True | 0/0/3 | <message Timestamp>; <message Timestamp>; <message Timestamp> |
| `capture_time.seconds` | scalar | int64 | False | False | 0/0/3 | 1761244500; 1761245139; 1761245699 |
| `capture_time.nanos` | scalar | int32 | False | False | 0/0/3 | 152824502; 483049206; 884594425 |
| `asset_id` | scalar | uint32 | False | False | 0/3/0 | 0; 0; 0 |
| `asset_id2` | scalar | string | False | False | 0/0/3 | 7aa0; 7aa0; 7aa0 |

</details>

## Relationship cardinality estimates

**All entries below are estimates only**, derived from value-set overlap and average occurrences per shared value across the full dataset. None of these are declared primary or foreign keys -- they require manual validation before any schema design decision.

| kind | normalized name | side A | side B | overlap | overlap% A / B | type comparable | cardinality estimate |
|---|---|---|---|---|---|---|---|
| cross_topic | asset_id | `cv_tracks.assets.asset_id` (0) | `track_states.measurements.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `cv_tracks.assets.asset_id` (0) | `track_states.measurements.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | asset_id | `cv_tracks.assets.asset_id` (0) | `track_states.ranked_camera_feeds.asset_id2` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `cv_tracks.assets.asset_id` (0) | `track_states.sensors.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `cv_tracks.assets.asset_id` (0) | `track_states.sensors.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | asset_id | `cv_tracks.assets.asset_id` (0) | `track_states.track_identity_matches.source_asset_id2` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `cv_tracks.assets.asset_id` (0) | `cv_detections.assets.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `cv_tracks.assets.asset_id` (0) | `radar_detections.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `cv_tracks.assets.asset_id` (0) | `radar_detections.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.measurements.asset_id` (0) | `track_states.measurements.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.measurements.asset_id` (0) | `track_states.ranked_camera_feeds.asset_id2` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.measurements.asset_id` (0) | `track_states.sensors.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.measurements.asset_id` (0) | `track_states.sensors.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.measurements.asset_id` (0) | `track_states.track_identity_matches.source_asset_id2` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.measurements.asset_id` (0) | `cv_detections.assets.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.measurements.asset_id` (0) | `radar_detections.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.measurements.asset_id` (0) | `radar_detections.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.measurements.asset_id2` (1) | `track_states.ranked_camera_feeds.asset_id2` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.measurements.asset_id2` (1) | `track_states.sensors.asset_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.measurements.asset_id2` (1) | `track_states.sensors.asset_id2` (1) | 1 | 1.0 / 1.0 | True | estimated_N_to_M |
| intra_topic | asset_id | `track_states.measurements.asset_id2` (1) | `track_states.track_identity_matches.source_asset_id2` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.measurements.asset_id2` (1) | `cv_detections.assets.asset_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.measurements.asset_id2` (1) | `radar_detections.asset_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.measurements.asset_id2` (1) | `radar_detections.asset_id2` (1) | 1 | 1.0 / 1.0 | True | estimated_N_to_M |
| intra_topic | asset_id | `track_states.ranked_camera_feeds.asset_id2` (0) | `track_states.sensors.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.ranked_camera_feeds.asset_id2` (0) | `track_states.sensors.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.ranked_camera_feeds.asset_id2` (0) | `track_states.track_identity_matches.source_asset_id2` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.ranked_camera_feeds.asset_id2` (0) | `cv_detections.assets.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.ranked_camera_feeds.asset_id2` (0) | `radar_detections.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.ranked_camera_feeds.asset_id2` (0) | `radar_detections.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.sensors.asset_id` (0) | `track_states.sensors.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.sensors.asset_id` (0) | `track_states.track_identity_matches.source_asset_id2` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.sensors.asset_id` (0) | `cv_detections.assets.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.sensors.asset_id` (0) | `radar_detections.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.sensors.asset_id` (0) | `radar_detections.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | asset_id | `track_states.sensors.asset_id2` (1) | `track_states.track_identity_matches.source_asset_id2` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.sensors.asset_id2` (1) | `cv_detections.assets.asset_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.sensors.asset_id2` (1) | `radar_detections.asset_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.sensors.asset_id2` (1) | `radar_detections.asset_id2` (1) | 1 | 1.0 / 1.0 | True | estimated_N_to_M |
| cross_topic | asset_id | `track_states.track_identity_matches.source_asset_id2` (0) | `cv_detections.assets.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.track_identity_matches.source_asset_id2` (0) | `radar_detections.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `track_states.track_identity_matches.source_asset_id2` (0) | `radar_detections.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | asset_id | `cv_detections.assets.asset_id` (0) | `radar_detections.asset_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | asset_id | `cv_detections.assets.asset_id` (0) | `radar_detections.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | asset_id | `radar_detections.asset_id` (0) | `radar_detections.asset_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | detection_id | `cv_tracks.assets.suppressed_detection_ids` (0) | `cv_tracks.tracks.last_associated_detection_id` (1868) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | detection_id | `cv_tracks.assets.suppressed_detection_ids` (0) | `track_states.license_plate.detection_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | detection_id | `cv_tracks.assets.suppressed_detection_ids` (0) | `track_states.measurements.detection_ids` (1717) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | detection_id | `cv_tracks.assets.suppressed_detection_ids` (0) | `cv_detections.assets.suppressed_detection_ids` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | detection_id | `cv_tracks.assets.suppressed_detection_ids` (0) | `cv_detections.detections.detection_id` (1911) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | detection_id | `cv_tracks.tracks.last_associated_detection_id` (1868) | `track_states.license_plate.detection_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | detection_id | `cv_tracks.tracks.last_associated_detection_id` (1868) | `track_states.measurements.detection_ids` (1717) | 0 | 0.0 / 0.0 | False | no_observed_overlap |
| cross_topic | detection_id | `cv_tracks.tracks.last_associated_detection_id` (1868) | `cv_detections.assets.suppressed_detection_ids` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | detection_id | `cv_tracks.tracks.last_associated_detection_id` (1868) | `cv_detections.detections.detection_id` (1911) | 1864 | 0.9979 / 0.9754 | True | estimated_1_to_N (cv_detections.detections.detection_id : cv_tracks.tracks.last_associated_detection_id) |
| intra_topic | detection_id | `track_states.license_plate.detection_id` (0) | `track_states.measurements.detection_ids` (1717) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | detection_id | `track_states.license_plate.detection_id` (0) | `cv_detections.assets.suppressed_detection_ids` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | detection_id | `track_states.license_plate.detection_id` (0) | `cv_detections.detections.detection_id` (1911) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | detection_id | `track_states.measurements.detection_ids` (1717) | `cv_detections.assets.suppressed_detection_ids` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | detection_id | `track_states.measurements.detection_ids` (1717) | `cv_detections.detections.detection_id` (1911) | 0 | 0.0 / 0.0 | False | no_observed_overlap |
| intra_topic | detection_id | `cv_detections.assets.suppressed_detection_ids` (0) | `cv_detections.detections.detection_id` (1911) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | id | `track_states.counts.source_id` (0) | `track_states.transponder_codes.mode_s.id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | id | `track_states.counts.source_id` (0) | `radar_detections.id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | id | `track_states.transponder_codes.mode_s.id` (0) | `radar_detections.id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | sensor_id | `cv_tracks.metadata.sensor_id` (0) | `track_states.counts.sensor_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | sensor_id | `cv_tracks.metadata.sensor_id` (0) | `track_states.measurements.sensor_id` (3) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | sensor_id | `cv_tracks.metadata.sensor_id` (0) | `track_states.sensors.sensor_id` (3) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | sensor_id | `cv_tracks.metadata.sensor_id` (0) | `cv_detections.metadata.sensor_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | sensor_id | `cv_tracks.metadata.sensor_id` (0) | `radar_detections.metadata.sensor_id` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | sensor_id | `track_states.counts.sensor_id` (0) | `track_states.measurements.sensor_id` (3) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | sensor_id | `track_states.counts.sensor_id` (0) | `track_states.sensors.sensor_id` (3) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | sensor_id | `track_states.counts.sensor_id` (0) | `cv_detections.metadata.sensor_id` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | sensor_id | `track_states.counts.sensor_id` (0) | `radar_detections.metadata.sensor_id` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | sensor_id | `track_states.measurements.sensor_id` (3) | `track_states.sensors.sensor_id` (3) | 3 | 1.0 / 1.0 | True | estimated_N_to_M |
| cross_topic | sensor_id | `track_states.measurements.sensor_id` (3) | `cv_detections.metadata.sensor_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | sensor_id | `track_states.measurements.sensor_id` (3) | `radar_detections.metadata.sensor_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | sensor_id | `track_states.sensors.sensor_id` (3) | `cv_detections.metadata.sensor_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | sensor_id | `track_states.sensors.sensor_id` (3) | `radar_detections.metadata.sensor_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | sensor_id | `cv_detections.metadata.sensor_id` (0) | `radar_detections.metadata.sensor_id` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | timestamp | `track_states.measurements.timestamp` (11967) | `track_states.timestamp` (7254) | 0 | 0.0 / 0.0 | True | no_observed_overlap |
| intra_topic | topic_id | `track_states.associated_detections.topic_id` (0) | `track_states.associated_detections.topic_id2` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | tower_id | `track_states.tower_id` (0) | `track_states.tower_id2` (1) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | track_id | `cv_tracks.tracks.track_id` (17) | `track_states.disposition_external.track_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | track_id | `cv_tracks.tracks.track_id` (17) | `track_states.disposition_external.track_id2` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | track_id | `cv_tracks.tracks.track_id` (17) | `track_states.parent_track_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | track_id | `cv_tracks.tracks.track_id` (17) | `track_states.track_id` (103) | 0 | 0.0 / 0.0 | True | no_observed_overlap |
| cross_topic | track_id | `cv_tracks.tracks.track_id` (17) | `track_states.track_id2` (103) | 0 | 0.0 / 0.0 | False | no_observed_overlap |
| cross_topic | track_id | `cv_tracks.tracks.track_id` (17) | `track_states.track_identity_matches.matched_track_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | track_id | `cv_tracks.tracks.track_id` (17) | `track_states.track_identity_matches.matched_track_id2` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | track_id | `cv_tracks.tracks.track_id` (17) | `radar_detections.detections.track_id` (81) | 0 | 0.0 / 0.0 | False | no_observed_overlap |
| intra_topic | track_id | `track_states.disposition_external.track_id` (0) | `track_states.disposition_external.track_id2` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | track_id | `track_states.disposition_external.track_id` (0) | `track_states.parent_track_id` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | track_id | `track_states.disposition_external.track_id` (0) | `track_states.track_id` (103) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | track_id | `track_states.disposition_external.track_id` (0) | `track_states.track_id2` (103) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | track_id | `track_states.disposition_external.track_id` (0) | `track_states.track_identity_matches.matched_track_id` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | track_id | `track_states.disposition_external.track_id` (0) | `track_states.track_identity_matches.matched_track_id2` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | track_id | `track_states.disposition_external.track_id` (0) | `radar_detections.detections.track_id` (81) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | track_id | `track_states.disposition_external.track_id2` (0) | `track_states.parent_track_id` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | track_id | `track_states.disposition_external.track_id2` (0) | `track_states.track_id` (103) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | track_id | `track_states.disposition_external.track_id2` (0) | `track_states.track_id2` (103) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | track_id | `track_states.disposition_external.track_id2` (0) | `track_states.track_identity_matches.matched_track_id` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | track_id | `track_states.disposition_external.track_id2` (0) | `track_states.track_identity_matches.matched_track_id2` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | track_id | `track_states.disposition_external.track_id2` (0) | `radar_detections.detections.track_id` (81) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | track_id | `track_states.parent_track_id` (0) | `track_states.track_id` (103) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | track_id | `track_states.parent_track_id` (0) | `track_states.track_id2` (103) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | track_id | `track_states.parent_track_id` (0) | `track_states.track_identity_matches.matched_track_id` (0) | 0 | None / None | True | no_observed_overlap |
| intra_topic | track_id | `track_states.parent_track_id` (0) | `track_states.track_identity_matches.matched_track_id2` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | track_id | `track_states.parent_track_id` (0) | `radar_detections.detections.track_id` (81) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | track_id | `track_states.track_id` (103) | `track_states.track_id2` (103) | 0 | 0.0 / 0.0 | False | no_observed_overlap |
| intra_topic | track_id | `track_states.track_id` (103) | `track_states.track_identity_matches.matched_track_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| intra_topic | track_id | `track_states.track_id` (103) | `track_states.track_identity_matches.matched_track_id2` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | track_id | `track_states.track_id` (103) | `radar_detections.detections.track_id` (81) | 0 | 0.0 / 0.0 | False | no_observed_overlap |
| intra_topic | track_id | `track_states.track_id2` (103) | `track_states.track_identity_matches.matched_track_id` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| intra_topic | track_id | `track_states.track_id2` (103) | `track_states.track_identity_matches.matched_track_id2` (0) | 0 | 0.0 / None | True | no_observed_overlap |
| cross_topic | track_id | `track_states.track_id2` (103) | `radar_detections.detections.track_id` (81) | 0 | 0.0 / 0.0 | True | no_observed_overlap |
| intra_topic | track_id | `track_states.track_identity_matches.matched_track_id` (0) | `track_states.track_identity_matches.matched_track_id2` (0) | 0 | None / None | True | no_observed_overlap |
| cross_topic | track_id | `track_states.track_identity_matches.matched_track_id` (0) | `radar_detections.detections.track_id` (81) | 0 | None / 0.0 | True | no_observed_overlap |
| cross_topic | track_id | `track_states.track_identity_matches.matched_track_id2` (0) | `radar_detections.detections.track_id` (81) | 0 | None / 0.0 | True | no_observed_overlap |
| intra_topic | uid | `track_states.atak_contact.uid` (0) | `track_states.target_uid` (0) | 0 | None / None | True | no_observed_overlap |

## Data-quality risk flags

- **identifier_never_observed** (`cv_tracks`, `assets.asset_id`): 'assets.asset_id' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`cv_tracks`, `assets.suppressed_detection_ids`): 'assets.suppressed_detection_ids' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **always_empty_field** (`cv_tracks`, `metadata.sensor_id`): 'metadata.sensor_id' is present in every one of its 35613 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **identifier_never_observed** (`track_states`, `associated_detections.topic_id`): 'associated_detections.topic_id' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`track_states`, `associated_detections.topic_id2`): 'associated_detections.topic_id2' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`track_states`, `atak_contact.uid`): 'atak_contact.uid' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **sparsely_populated_field** (`track_states`, `counts.class_id`): 'counts.class_id' is null/unset in 100.0% of observed occurrences.
- **sparsely_populated_field** (`track_states`, `counts.sensor_id`): 'counts.sensor_id' is null/unset in 100.0% of observed occurrences.
- **sparsely_populated_field** (`track_states`, `counts.source_id`): 'counts.source_id' is null/unset in 100.0% of observed occurrences.
- **identifier_never_observed** (`track_states`, `disposition_external.track_id`): 'disposition_external.track_id' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`track_states`, `disposition_external.track_id2`): 'disposition_external.track_id2' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **always_empty_field** (`track_states`, `disposition_timestamp`): 'disposition_timestamp' is present in every one of its 11630 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **always_empty_field** (`track_states`, `fragment_id`): 'fragment_id' is present in every one of its 11630 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **identifier_never_observed** (`track_states`, `license_plate.detection_id`): 'license_plate.detection_id' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **always_empty_field** (`track_states`, `measurements.asset_id`): 'measurements.asset_id' is present in every one of its 11992 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **duplicate_looking_identifier** (`track_states`, `measurements.asset_id2`): 1 value(s) of 'measurements.asset_id2' repeat within a single message's batch, which is unexpected for an identifier-shaped field.
- **duplicate_looking_identifier** (`track_states`, `measurements.detection_ids`): 65 value(s) of 'measurements.detection_ids' repeat within a single message's batch, which is unexpected for an identifier-shaped field.
- **duplicate_looking_identifier** (`track_states`, `measurements.sensor_id`): 1 value(s) of 'measurements.sensor_id' repeat within a single message's batch, which is unexpected for an identifier-shaped field.
- **always_empty_field** (`track_states`, `parent_track_id`): 'parent_track_id' is present in every one of its 11630 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **identifier_never_observed** (`track_states`, `ranked_camera_feeds.asset_id2`): 'ranked_camera_feeds.asset_id2' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **always_empty_field** (`track_states`, `sensors.asset_id`): 'sensors.asset_id' is present in every one of its 13591 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **duplicate_looking_identifier** (`track_states`, `sensors.asset_id2`): 1 value(s) of 'sensors.asset_id2' repeat within a single message's batch, which is unexpected for an identifier-shaped field.
- **always_empty_field** (`track_states`, `target_uid`): 'target_uid' is present in every one of its 11630 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **always_empty_field** (`track_states`, `tower_id`): 'tower_id' is present in every one of its 11630 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **identifier_never_observed** (`track_states`, `track_identity_matches.matched_track_id`): 'track_identity_matches.matched_track_id' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`track_states`, `track_identity_matches.matched_track_id2`): 'track_identity_matches.matched_track_id2' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`track_states`, `track_identity_matches.source_asset_id2`): 'track_identity_matches.source_asset_id2' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`track_states`, `transponder_codes.mode5.mode5_platform_id`): 'transponder_codes.mode5.mode5_platform_id' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`track_states`, `transponder_codes.mode_s.id`): 'transponder_codes.mode_s.id' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`cv_detections`, `assets.asset_id`): 'assets.asset_id' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`cv_detections`, `assets.suppressed_detection_ids`): 'assets.suppressed_detection_ids' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **always_empty_field** (`cv_detections`, `detectors.detector_id`): 'detectors.detector_id' is present in every one of its 7121 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **always_empty_field** (`cv_detections`, `metadata.sensor_id`): 'metadata.sensor_id' is present in every one of its 7121 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **always_empty_field** (`radar_detections`, `asset_id`): 'asset_id' is present in every one of its 2902 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **identifier_never_observed** (`radar_detections`, `detections.debug.rada_v6_debug.desired_revisit_time`): 'detections.debug.rada_v6_debug.desired_revisit_time' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`radar_detections`, `detections.debug.rada_v6_debug.optimal_revisit_time`): 'detections.debug.rada_v6_debug.optimal_revisit_time' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **identifier_never_observed** (`radar_detections`, `detections.detection_metadata.echoshield.lifetime`): 'detections.detection_metadata.echoshield.lifetime' is an identifier-shaped field but its containing repeated group was empty in every message -- zero occurrences observed across the entire dataset.
- **always_empty_field** (`radar_detections`, `id`): 'id' is present in every one of its 2902 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
- **always_empty_field** (`radar_detections`, `metadata.sensor_id`): 'metadata.sensor_id' is present in every one of its 2902 observed occurrences but always holds the scalar default value (e.g. empty string / 0) -- never meaningfully populated in this dataset. Possibly scrubbed by sanitization, or simply unused by this data source.
