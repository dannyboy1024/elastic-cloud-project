<template>
    <el-container>
        <el-tabs tab-position="left" @tab-click="handleTabClick" v-model="activeName" style="width: 3000px;">
            <el-tab-pane label="Image Upload and Retrieve" name="1" style="text-align: left;">
                <h1>Upload Image</h1>
                <el-row>
                    <el-col :span="8">
                        &nbsp;&nbsp;&nbsp;Please input the key value ：
                    </el-col>
                    <el-col :span="16">
                        <el-input v-model="uploadInfo.key" clearable style="width: 30%;"></el-input>
                    </el-col>
                </el-row>
                <br>
                <el-row>
                    <el-col :span="8">
                        <br> &nbsp;&nbsp;&nbsp;Please select one Image ：
                    </el-col>
                    <el-col :span="16">
                        <el-upload ref="child" action="#" list-type="picture-card" :auto-upload="false"
                            :class="{ hideUpload: uploadInfo.hideUploadEdit }"
                            :on-change="(file, fileList) => handlePicChange(file, fileList)">
                            <i slot="default" class="el-icon-plus"></i>
                            <div slot="file" slot-scope="{file}">
                                <img class="el-upload-list__item-thumbnail" :src="file.url" alt="">
                                <span class="el-upload-list__item-actions">
                                    <span class="el-upload-list__item-preview" @click="handlePictureCardPreview(file)">
                                        <i class="el-icon-zoom-in"></i>
                                    </span>
                                    <!-- <span v-if="!uploadInfo.disabled" class="el-upload-list__item-delete"
                                    @click="handleDownload(file)">
                                    <i class="el-icon-download"></i>
                                </span> -->
                                    <span v-if="!uploadInfo.disabled" class="el-upload-list__item-delete"
                                        @click="handlePicRemove()">
                                        <i class="el-icon-delete"></i>
                                    </span>
                                </span>
                            </div>
                        </el-upload>
                    </el-col>
                </el-row>
                <br>
                <el-row>
                    <el-col :span="8" :offset="8"><el-button size="small" type="primary"
                            @click="submitUpload">Submit</el-button></el-col>
                </el-row>
                <el-dialog :visible.sync="uploadInfo.dialogVisible">
                    <img width="100%" :src="uploadInfo.dialogImageUrl" alt="">
                </el-dialog>
                <h1>Retrieve Image</h1>
                <el-row>
                    <el-col :span="8">
                        &nbsp;&nbsp;&nbsp;Please input the key value ：
                    </el-col>
                    <el-col :span="16">
                        <el-input v-model="retrieveInfo.key" clearable style="width: 30%;"></el-input>
                    </el-col>
                </el-row>
                <br>
                <el-row>
                    <el-col :span="8" :offset="8"><el-button size="small" type="primary"
                            @click="retrieveImage">Retrieve</el-button></el-col>
                </el-row>
                <br>
                <el-row>
                    <el-col :offset="7">
                        <el-image v-if="retrieveInfo.showImage" style="width: 200px;height: 200px;"
                            :src="retrieveInfo.imageUrl" fit="scale-down">
                            <div slot="error" class="image-slot">
                                <i class="el-icon-picture-outline"></i>
                            </div>
                        </el-image>
                    </el-col>
                </el-row>
            </el-tab-pane>
            <el-tab-pane label="Keys info" name="2" style="text-align: left; ">
                &nbsp;&nbsp;&nbsp;keys in RDS :
                &nbsp;&nbsp;&nbsp;
                <!-- <el-tooltip class="item" effect="dark" content="delete all the keys" placement="right-start">
                    <el-popconfirm confirm-button-text='delete' cancel-button-text='cancel' icon="el-icon-info"
                        icon-color="red" title="Sure to delete?" @confirm="deleteKey('delete all keys', 2)">
                        <el-button slot="reference" icon="el-icon-delete" type="text"
                            style="margin-top: 7px;"></el-button>
                    </el-popconfirm>
                </el-tooltip> -->
                <div id="keysTable">
                    <el-row v-for="(item, index) in keysList" :key="index">
                        <el-col :span="4" :offset="3">
                            <p>{{ item }}</p>
                        </el-col>
                        <!-- <el-col :span="4">
                            <el-popconfirm confirm-button-text='delete' cancel-button-text='cancel' icon="el-icon-info"
                                icon-color="red" title="Sure to delete?" @confirm="deleteKey(item, 1)">
                                <el-button slot="reference" icon="el-icon-delete" type="text"
                                    style="margin-top: 7px;"></el-button>
                            </el-popconfirm>
                        </el-col> -->
                        <br><br>
                    </el-row>
                </div>
                <br>
                <div id="keysCacheTable">
                    &nbsp;&nbsp;&nbsp;keys in Cache :
                    &nbsp;&nbsp;&nbsp;
                    <el-row v-for="(item, index) in keysCacheList" :key="index">
                        <el-col :span="4" :offset="3">
                            <p>{{ item }}</p>
                        </el-col>
                        <br><br>
                    </el-row>
                </div>
            </el-tab-pane>
            <!-- <el-tab-pane label="Memcache Management" name="3" style="text-align: left; ">
                <h1>Mem-cache Parameters</h1>
                <el-row>
                    <el-col :span="7">
                        &nbsp;&nbsp;&nbsp;Need cache?：
                    </el-col>
                    <el-switch v-model="cacheParams.cacheMode" active-color="#13ce66" inactive-color="#ff4949" />
                </el-row>
                <br>
                <el-row>
                    <el-col :span="7">
                        &nbsp;&nbsp;&nbsp;Capacity Size：
                    </el-col>
                    <el-col :span="12">
                        <el-input v-model="cacheParams.capacity" type="number" style="width: 60%;">
                        </el-input>&nbsp;&nbsp;MB</el-col>

                </el-row>
                <br>
                <el-row>
                    <el-col :span="7">
                        &nbsp;&nbsp;&nbsp;Replacement Policy：
                    </el-col>
                    <el-col :span="12">
                        <el-select v-model="cacheParams.policy" style="width: 60%;" placeholder="">
                            <el-option v-for="item in cacheParams.policyOptions" :key="item.value" :label="item.label"
                                :value="item.value">
                            </el-option>
                        </el-select>
                    </el-col>
                </el-row>
                <br>
                <el-row>
                    <el-col :span="6" :offset="15">
                        <el-popconfirm confirm-button-text='submit' cancel-button-text='cancel' icon="el-icon-info"
                            icon-color="red" title="Sure to submit?" @confirm="submitParams">
                            <el-button slot="reference" type="primary">submit changes</el-button>
                        </el-popconfirm>
                    </el-col>
                </el-row>
                <el-row>
                    <el-col :span="7">
                        &nbsp;&nbsp;&nbsp;
                        <el-popconfirm confirm-button-text='submit' cancel-button-text='cancel' icon="el-icon-info"
                            icon-color="red" title="Sure to clear?" @confirm="clearCache">
                            <el-button slot="reference" type="primary">clear cache</el-button>
                        </el-popconfirm>
                    </el-col>
                </el-row>
                <br>
                <el-row>
                    <el-col :span="7">
                        &nbsp;&nbsp;&nbsp;
                        <el-button type="primary" @click="showCacheKeys">show keys stored in
                            Cache</el-button>
                    </el-col>
                </el-row>
                <div id="keysCacheTable">
                    <el-row v-for="(item, index) in keysCacheList" :key="index">
                        <el-col :span="4" :offset="3">
                            <p>{{ item }}</p>
                        </el-col>
                        <br><br>
                    </el-row>
                </div>
                <h1>Current statistics</h1>
                <el-table :data="tableData" style="width: 100%">
                    <el-table-column prop="time" label="time(s)" width="150">
                    </el-table-column>
                    <el-table-column prop="hitRate" label="hitRate" width="150">
                    </el-table-column>
                    <el-table-column prop="hitRate" label="hitRate" width="150">
                    </el-table-column>
                    <el-table-column prop="missRate" label="missRate" width="150">
                    </el-table-column>
                    <el-table-column prop="numItems" label="numItems" width="150">
                    </el-table-column>
                    <el-table-column prop="numReqs" label="numReqs" width="150">
                    </el-table-column>
                    <el-table-column prop="totalSize" label="totalSize(Bytes)" width="150">
                    </el-table-column>
                </el-table>
            </el-tab-pane> -->
        </el-tabs>
    </el-container>
</template>

<script>
import axios from 'axios';
export default {
    data() {
        return {
            charts: "",
            activeName: '1',
            uploadInfo: {
                key: '',
                dialogImageUrl: '',
                disabled: false,
                dialogVisible: false,
                hideUploadEdit: false,
                lengthLimit: 1
            },
            retrieveInfo: {
                key: '',
                imageUrl: '',
                showImage: false
            },
            keysList: [],
            keysCacheList: [],
            cacheParams: {
                capacity: 0,
                policyOptions: [{
                    value: 'Random Replacement',
                    label: 'Random Replacement'
                },
                {
                    value: 'Least Recently Used',
                    label: 'Least Recently Used'
                }
                ],
                policy: '',
                cacheMode: true
            },
            tableData: [],
            timer_10: null,
            nodeNums: 1
        }
    },
    created() {
        this.timer_10 = window.setInterval(() => {
            setTimeout(this.polling(), 0);

        }, 10000)
    },
    destroyed() {
        window.clearInterval(this.timer_10);
    },
    methods: {
        polling() {
            axios
                .post('/route/api/getNumNodes')
                .then(res => {
                    if (res.data) {
                        console.log("retrieve node numbers:", res);
                        if (this.nodeNums != res.data.numNodes) {
                            this.$message.warning('The number of nodes has changed to ' + res.data.numNodes + ' !');
                            this.nodeNums = res.data.numNodes;
                        }
                    }
                    else {
                        console.log("Fail to get node numbers!");
                    }
                })
                .catch(error => {
                    // this.$message.warning('Fail to get node numbers!');
                    console.error(error);
                })
        },
        handleTabClick(tab) {
            this.retrieveInfo.imageUrl = ''
            this.retrieveInfo.showImage = false
            if (tab.index == 1) { //获取keys的配置
                // const url = this.baseUrl + 'getKeys';
                axios
                    .post('/route/allKeyDB')
                    .then(res => {
                        if (res.data) {
                            console.log("retrieve keys info:", res);
                            this.keysList = res.data;
                        }
                        else {
                            console.log("Fail to get keys!");
                            this.keysList = [];
                        }
                    })
                    .catch(error => {
                        this.$message.warning('Fail to get keys!');
                        console.error(error);
                    })
                axios
                    .post('/route/api/list_keys')
                    .then(res => {
                        if (res.data) {
                            console.log("retrieve keys info:", res);
                            this.keysCacheList = res.data.keys;
                        }
                        else {
                            console.log("Fail to get keys!");
                            this.keysCacheList = [];
                        }
                    })
                    .catch(error => {
                        this.$message.warning('Fail to get keys!');
                        console.error(error);
                    })
            }
            // else if (tab.index == 2) {
            //     // const url = this.baseUrl + 'params';
            //     axios
            //         .get('/api/params')
            //         .then(res => {
            //             console.log(res.data);
            //             if (res.data) {
            //                 let data = res.data
            //                 this.cacheParams.capacity = data.size
            //                 this.cacheParams.policy = (data.policy == 'RR' ? 'Random Replacement' : 'Least Recently Used');
            //                 this.cacheParams.cacheMode = (data.operation == 'true' ? true : false)
            //             } else {
            //                 this.$message.warning('Cache configuration\'s params are empty!');
            //                 console.error('Cache configuration\'s params are empty');
            //             }
            //         })
            //         .catch(error => {
            //             this.$message.warning('Fail to get cache configuration!');
            //             console.error(error);
            //         })
            //     axios.get('/api/requestCurrentStat')
            //         .then(res => {
            //             console.log(res.data);
            //             let data = res.data;

            //             let hitRate = data.hitRate;
            //             for (let index = 0; index < hitRate.length; index++) {
            //                 let tableItem = {};
            //                 tableItem['time'] = index * 5;
            //                 tableItem['hitRate'] = data.hitRate[index];
            //                 tableItem['missRate'] = data.missRate[index];
            //                 tableItem['numItems'] = data.numItems[index];
            //                 tableItem['numReqs'] = data.numReqs[index];
            //                 tableItem['totalSize'] = data.totalSize[index];
            //                 this.tableData.push(tableItem);
            //             }
            //         })
            // }
        },
        handlePicRemove() {
            console.log(this.$refs.child.uploadFiles);
            let fileList = this.$refs.child.uploadFiles;
            fileList.pop();
            this.uploadInfo.hideUploadEdit = (fileList.length >= this.uploadInfo.lengthLimit);
            // this.$refs.child.uploadFiles.forEach((v, index) => {
            //     if (file.name === v.name && file.url === v.url) {
            //         this.$refs.child.uploadFiles.splice(index, 1);
            //     }
            // });
        },
        handlePictureCardPreview(file) {
            this.uploadInfo.dialogImageUrl = file.url;
            this.uploadInfo.dialogVisible = true;
        },
        // handleDownload(file) {
        //     console.log(file);
        // },
        handlePicChange(file, fileList) {
            console.log(fileList);
            this.uploadInfo.hideUploadEdit = (fileList.length >= this.uploadInfo.lengthLimit);
        },
        submitUpload() {
            console.log("Upload Info:", this.uploadInfo);
            console.log(this.$refs.child.uploadFiles);
            // let url = this.baseUrl + 'image'
            if (this.uploadInfo.key == "") {
                this.$message.warning('Key is empty, please enter the key of the image!');
            }
            if (this.$refs.child.uploadFiles.length !== 0) {
                let form = new FormData()
                form.append('key', this.uploadInfo.key);
                form.append('file', JSON.stringify(this.$refs.child.uploadFiles[0]))
                axios.post('/route/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
                    .then(res => {
                        console.log('upload request return info:', res);
                        this.uploadInfo.key = '';
                        if (res.status == 200) {
                            this.$refs.child.uploadFiles.pop();
                            this.uploadInfo.hideUploadEdit = (this.$refs.child.uploadFiles.length >= this.uploadInfo.lengthLimit);
                        } else {
                            this.$message.warning('Fail to upload!')
                        }
                    })
                    .catch(error => {
                        console.error(error);
                    })
            } else {
                this.$message.warning('Image is empty, please choose one image!');
            }

        },
        retrieveImage() {
            console.log("Retrieve key is: ", this.retrieveInfo.key);
            if (this.retrieveInfo.key == '') {
                this.$message.warning('Key is empty, please enter the key of the image!');
                this.retrieveInfo.showImage = false
            } else {
                // let url = '/api/key/' + this.retrieveInfo.key
                axios({
                    method: 'POST',
                    url: '/route/key/' + this.retrieveInfo.key
                }).then(res => {
                    console.log('retrieve image info: ', res.data);
                    if (res.status == 200) {
                        if (res.data["success"] == 'false') {
                            this.$message.warning('File Not Found!')
                            this.retrieveInfo.imageUrl = ''
                            this.retrieveInfo.showImage = false
                        }
                        else {
                            let content = eval('(' + res.data.content + ')')
                            this.retrieveInfo.imageUrl = content.url
                            this.retrieveInfo.showImage = true
                        }
                    } else {
                        this.$message.warning('Fail to retrieve!');
                        this.retrieveInfo.imageUrl = ''
                        this.retrieveInfo.showImage = false

                    }
                }).catch(error => {
                    console.error(error);
                    this.retrieveInfo.imageUrl = ''
                    this.retrieveInfo.showImage = false
                })
            }
        },
        // deleteKey(key, type) {
        //     if (type == 1) {//单个删除
        //         console.log("The key about to be deleted is: ", key);
        //     } else if (type == 2) {
        //         console.log("Delete all the keys");
        //     }
        //     axios({
        //         url: '/api/delete_all',
        //         data: { 'key': key },
        //         method: 'POST'
        //     })
        //         .then(res => {
        //             console.log(res);
        //             if (res.data != 'Fail') {
        //                 this.keysList = [];
        //             } else {
        //                 this.$message.warning('Fail to delete keys!');
        //             }
        //         })
        //         .catch(error => {
        //             this.$message.warning('Fail to delete or retrieve keys!');
        //             console.error(error);
        //         })
        // },
        // clearCache() {
        //     console.log("clear cache");
        //     axios({
        //         url: '/api/clear',
        //         method: 'POST'
        //     })
        //         .then(res => {
        //             console.log(res);
        //         })
        //         .catch(error => {
        //             this.$message.warning('Fail to clear caches!');
        //             console.error(error);
        //         })
        // },
        // submitParams() {
        //     console.log('Changing mem-cache parameters into:', this.cacheParams);
        //     //todo：提交修改
        //     let params = {
        //         'size': this.cacheParams.capacity,
        //         'policy': this.cacheParams.policy == 'Least Recently Used' ? 'LRU' : 'RR',
        //         'operation': '' + this.cacheParams.cacheMode + ''
        //     }
        //     axios({
        //         method: 'PUT',
        //         url: '/api/params',
        //         data: { 'params': params }
        //     })
        //         .then(res => {
        //             console.log(res.data);
        //             if (res.data) {
        //                 let data = res.data
        //                 this.cacheParams.capacity = data.size
        //                 this.cacheParams.policy = (data.policy == 0 ? 'Random Replacement' : 'Least Recently Used');
        //             } else {
        //                 this.$message.warning('Cache configuration\'s params are empty!');
        //                 console.error('Cache configuration\'s params are empty');
        //             }
        //         })
        //         .catch(error => {
        //             this.$message.warning('Fail to change cache configuration!');
        //             console.error(error);
        //         })
        // },
        showCacheKeys() {

        }
    },
};
</script>

<style>
.hideUpload .el-upload.el-upload--picture-card {
    display: none;
}
</style>
